"""SSH 提交签名核验（AUTO-CONNECT-001 r2 要求 1）。

只做一件事：用本机钉住的公钥核验某个提交的 SSH 签名，并要求
- `ssh-keygen -Y verify` 等价路径返回 Good（这里用 `git verify-commit` + allowedSigners）
- 签名身份等于钉住的身份
- 指纹等于钉住的指纹（指纹也会从公钥本身重算，防止换了 key 但照抄指纹）

不读取私钥，不读取 token，不访问网络。`%G?=N` 且没有 allowedSigners 时不算通过。
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .common import GitError

_FP_RE = re.compile(r"SHA256:([A-Za-z0-9+/]+)")


def _normalize_repo(url: str) -> str:
    """把 https://host/org/repo.git 与 https://host/org/repo 视为同一个仓库。"""
    text = (url or "").strip().lower().rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    return text


@dataclass
class SignerRule:
    identity: str
    public_key: str
    fingerprint: str
    repo: str = ""
    ref: str = ""
    note: str = ""

    def applies_to(self, repo_url: str, ref: str) -> bool:
        if self.repo and self.repo.strip() \
                and _normalize_repo(self.repo) != _normalize_repo(repo_url):
            return False
        if self.ref and self.ref.strip() and self.ref.strip() != (ref or "").strip():
            return False
        return True


@dataclass
class SignatureResult:
    ok: bool
    status: str                      # good | bad | unsigned | no_signer | error
    fingerprint: str | None = None
    identity: str | None = None
    reasons: list[str] = field(default_factory=list)
    method: str = "git-ssh-allowed-signers"

    def as_dict(self) -> dict:
        return {"status": self.status, "fingerprint": self.fingerprint,
                "identity": self.identity, "ok": self.ok, "reasons": self.reasons,
                "method": self.method}


def load_signers(payload: dict | None) -> list[SignerRule]:
    """从信任文件读取 signers（缺省或格式错误时返回空，不抛错）。"""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("signers")
    if not isinstance(raw, list):
        return []
    out: list[SignerRule] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("identity") or "").strip()
        public_key = str(item.get("public_key") or "").strip()
        fingerprint = str(item.get("fingerprint") or "").strip()
        if not (identity and public_key and fingerprint):
            continue
        out.append(SignerRule(
            identity=identity,
            public_key=public_key,
            fingerprint=fingerprint,
            repo=str(item.get("repo") or "").strip(),
            ref=str(item.get("ref") or "").strip(),
            note=str(item.get("note") or "").strip(),
        ))
    return out


def normalize_fingerprint(value: str | None) -> str:
    if not value:
        return ""
    match = _FP_RE.search(value)
    if match:
        return "SHA256:" + match.group(1)
    return value.strip()


def public_key_fingerprint(public_key: str, timeout: float = 20.0) -> str | None:
    """调用 ssh-keygen 重算公钥指纹（SHA256:...）。"""
    try:
        proc = subprocess.run(["ssh-keygen", "-lf", "-"], input=public_key + "\n",
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    match = _FP_RE.search(proc.stdout or "")
    return "SHA256:" + match.group(1) if match else None


def _git(args: list[str], cwd: Path, timeout: float = 60.0) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, env=env)


def verify_commit_signature(repo_dir: Path, commit: str, signers: list[SignerRule],
                            repo_url: str = "", ref: str = "") -> SignatureResult:
    """核验 commit 的 SSH 签名。任何一步不满足都返回 ok=False 并给出原因。"""
    applicable = [s for s in signers if s.applies_to(repo_url, ref)]
    if not applicable:
        return SignatureResult(False, "no_signer",
                               reasons=["没有适用于该仓库/分支的钉住公钥"])
    if not commit:
        return SignatureResult(False, "unsigned", reasons=["没有清单提交"])

    reasons: list[str] = []
    for signer in applicable:
        actual_key_fp = public_key_fingerprint(signer.public_key)
        if not actual_key_fp:
            reasons.append("无法计算钉住公钥的指纹（ssh-keygen 不可用？）")
            continue
        if normalize_fingerprint(actual_key_fp) != normalize_fingerprint(signer.fingerprint):
            reasons.append("钉住公钥指纹不符（配置 %s / 实际 %s）"
                           % (signer.fingerprint, actual_key_fp))
            continue

        with tempfile.TemporaryDirectory(prefix="ioswb-signers-") as tmp:
            allowed = Path(tmp) / "allowed_signers"
            allowed.write_text("%s %s\n" % (signer.identity, signer.public_key), encoding="utf-8")
            base = ["-c", "gpg.format=ssh",
                    "-c", "gpg.ssh.allowedSignersFile=%s" % allowed]
            verify = _git(base + ["verify-commit", commit], repo_dir)
            if verify.returncode != 0:
                detail = ((verify.stderr or verify.stdout) or "").strip().splitlines()
                reasons.append("签名校验未通过：%s" % (detail[0][:160] if detail else "无输出"))
                continue
            fmt = _git(base + ["log", "-1", "--format=%G?%n%GF%n%GS", commit], repo_dir)
            lines = (fmt.stdout or "").splitlines()
            status = (lines[0].strip() if lines else "")
            fp = normalize_fingerprint(lines[1].strip() if len(lines) > 1 else "")
            identity = lines[2].strip() if len(lines) > 2 else ""
            if status != "G":
                reasons.append("git 报告签名状态=%s（非 Good）" % (status or "unknown"))
                continue
            if identity != signer.identity:
                reasons.append("签名身份不符（钉 %s / 实际 %s）" % (signer.identity, identity))
                continue
            if fp != normalize_fingerprint(signer.fingerprint):
                reasons.append("签名指纹不符（钉 %s / 实际 %s）"
                               % (signer.fingerprint, fp))
                continue
            return SignatureResult(True, "good", fingerprint=fp, identity=identity)

    return SignatureResult(False, "bad", reasons=reasons or ["签名不满足钉住公钥"])
