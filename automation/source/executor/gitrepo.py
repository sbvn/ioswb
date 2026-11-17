"""Git 操作封装。

约束：
- 使用本机现有正常认证（credential helper）；不读取、不打印任何凭据。
- 不强推（不允许 --force / --force-with-lease 覆盖他人提交）。
- 只在 automation/state/work 下的临时克隆里操作，不碰业务目录。
- 推送失败只意味着“回执没传上去”，绝不允许因此重新执行任务。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Iterable

from .common import GitError, ensure_dir

_URL_CRED = re.compile(r"(https?://)([^/@\s]+)@", re.IGNORECASE)


def scrub(text: str) -> str:
    """去掉 URL 里可能存在的 userinfo，避免凭据进入日志。"""
    return _URL_CRED.sub(r"\1***@", text or "")


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env.setdefault("GIT_AUTHOR_NAME", "DeepSeek Harness")
    env.setdefault("GIT_COMMITTER_NAME", "DeepSeek Harness")
    env.pop("GIT_ASKPASS", None)
    return env


def run_git(args: Iterable[str], cwd: Path | None = None, check: bool = True,
            timeout: float = 120.0, stdin: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["git"] + list(args)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            input=stdin,
            env=_git_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # git 不存在
        raise GitError("git 不可用: %s" % exc) from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError("git 超时: %s" % scrub(" ".join(cmd))) from exc
    if check and proc.returncode != 0:
        detail = scrub((proc.stderr or proc.stdout or "").strip())[:800]
        raise GitError("git %s 失败(exit=%s): %s" % (args and list(args)[0], proc.returncode, detail))
    return proc


class RepoCache:
    """每个 remote+branch 一个本地镜像克隆，只用于读和上传。"""

    def __init__(self, root: Path, url: str, branch: str) -> None:
        self.root = root
        self.url = url
        self.branch = branch
        self.path = root / "repo"

    def ensure_clone(self) -> Path:
        ensure_dir(self.root)
        if not (self.path / ".git").exists():
            run_git(["clone", "--quiet", "--no-checkout", self.url, str(self.path)], timeout=300)
        return self.path

    def fetch(self) -> str:
        path = self.ensure_clone()
        run_git(["fetch", "--quiet", "--prune", "origin", self.branch], cwd=path, timeout=300)
        proc = run_git(["rev-parse", "origin/%s" % self.branch], cwd=path)
        return proc.stdout.strip()

    def read_file(self, commit: str, rel_path: str) -> bytes:
        path = self.ensure_clone()
        proc = subprocess.run(
            ["git", "show", "%s:%s" % (commit, rel_path)],
            cwd=str(path),
            env=_git_env(),
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise GitError("读取 %s@%s 失败: %s" % (rel_path, commit[:8], scrub(proc.stderr.decode("utf-8", "replace"))[:400]))
        return proc.stdout

    def file_exists(self, commit: str, rel_path: str) -> bool:
        path = self.ensure_clone()
        proc = run_git(["cat-file", "-e", "%s:%s" % (commit, rel_path)], cwd=path, check=False)
        return proc.returncode == 0

    def rev_parse(self, ref: str) -> str | None:
        path = self.ensure_clone()
        proc = run_git(["rev-parse", "--verify", "--quiet", ref], cwd=path, check=False)
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        path = self.ensure_clone()
        proc = run_git(["merge-base", "--is-ancestor", ancestor, descendant], cwd=path, check=False)
        return proc.returncode == 0

    def head_commit(self, ref: str = "HEAD") -> str | None:
        return self.rev_parse(ref)

    def file_commit(self, head: str, rel_path: str) -> str | None:
        """返回该路径最后一次被修改的提交（用于把摘要钉绑定到真正携带清单的 commit）。"""
        path = self.ensure_clone()
        proc = run_git(["rev-list", "-1", head, "--", rel_path], cwd=path, check=False)
        if proc.returncode != 0:
            return None
        value = proc.stdout.strip()
        return value or None

    # ---------- 签名校验（只读） ----------
    def verify_signature(self, commit: str) -> dict:
        path = self.ensure_clone()
        proc = run_git(["log", "-1", "--format=%G?%n%GF", commit], cwd=path, check=False)
        if proc.returncode != 0:
            return {"status": "unavailable", "fingerprint": None}
        lines = (proc.stdout or "").splitlines()
        status = lines[0].strip() if lines else ""
        fingerprint = lines[1].strip() if len(lines) > 1 else ""
        return {
            "status": {"G": "good", "B": "bad", "U": "unknown_validity", "X": "expired",
                       "Y": "expired_key", "R": "revoked_key", "E": "missing_key",
                       "N": "unsigned"}.get(status, status or "unavailable"),
            "fingerprint": fingerprint or None,
        }

    # ---------- 上传 ----------
    def commit_and_push_file(self, rel_path: str, data: bytes, message: str,
                             retries: int = 3) -> dict:
        """在最新远端头上追加一个只含该文件的提交并推送。

        失败只返回 status=failed，由调用方标记 upload_failed；绝不重跑任务。
        """
        path = self.ensure_clone()
        last_error = ""
        for attempt in range(1, max(1, retries) + 1):
            try:
                run_git(["fetch", "--quiet", "--prune", "origin", self.branch], cwd=path, timeout=300)
                head = run_git(["rev-parse", "origin/%s" % self.branch], cwd=path).stdout.strip()
                run_git(["checkout", "--quiet", "--force", "--detach", head], cwd=path, timeout=120)
                target = path / rel_path
                ensure_dir(target.parent)
                with open(target, "wb") as handle:
                    handle.write(data)
                run_git(["add", "--", rel_path], cwd=path)
                run_git(["commit", "--quiet", "-m", message], cwd=path)
                local = run_git(["rev-parse", "HEAD"], cwd=path).stdout.strip()
                # 普通 push：不带 --force/--force-with-lease。
                push = run_git(["push", "--quiet", "origin", "HEAD:refs/heads/%s" % self.branch],
                               cwd=path, check=False, timeout=300)
                if push.returncode == 0:
                    return {"status": "pushed", "commit": local, "attempts": attempt,
                            "rel_path": rel_path}
                last_error = scrub((push.stderr or push.stdout or "").strip())[:600]
                # 非快进或临时错误：回到干净状态，下一轮在最新头上重建提交。
                run_git(["checkout", "--quiet", "--force", "--detach", "origin/%s" % self.branch],
                        cwd=path, check=False)
            except GitError as exc:
                last_error = scrub(str(exc))[:600]
        return {"status": "failed", "commit": None, "attempts": retries, "rel_path": rel_path,
                "error": last_error}
