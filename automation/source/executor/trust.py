"""发布身份核验（本机预设信任规则）。

明确不做的事：
- 不相信 git 提交作者名；
- 不相信任务正文自称“01 发布”；
- 不相信清单里的 publisher 字段。

只认本机信任文件里预先写下的三种凭据之一：
1. pinned_manifest_sha256 —— 操作者事先核对外带渠道后钉住的清单内容摘要；
2. pinned_commit         —— 操作者钉住的清单提交或任务提交 SHA；
3. signed_commit         —— 提交签名可验证，且签名指纹在 allowlist 内。

规则文件不存在或规则为空 => trust_unconfigured，禁止任何真实自动执行。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .common import SCHEMA_TRUST, SHA40_RE, SHA64_RE, TrustError

RULE_KINDS = ("pinned_manifest_sha256", "pinned_commit", "signed_commit_fingerprints")


@dataclass
class TrustConfig:
    path: str
    rules: dict[str, list[str]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        return any(bool(self.rules.get(kind)) for kind in RULE_KINDS)

    def describe(self) -> str:
        if not self.configured:
            return "未配置信任规则"
        parts = []
        for kind in RULE_KINDS:
            values = self.rules.get(kind) or []
            if values:
                parts.append("%s=%d 条" % (kind, len(values)))
        return "，".join(parts)


@dataclass
class TrustDecision:
    trusted: bool
    rule: str | None
    reasons: list[str]
    scope: str = "none"          # "manifest"（对整份清单生效）| "task"（只对单个任务生效）| "none"
    task_commit: str | None = None

    def summary(self) -> str:
        if self.trusted:
            return "trusted by %s（scope=%s）" % (self.rule, self.scope)
        return "untrusted: %s" % "; ".join(self.reasons)


def load_trust(path) -> TrustConfig:
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return TrustConfig(path=str(p), rules={}, raw={})
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TrustError("信任文件不是合法 JSON: %s" % exc) from exc
    if not isinstance(payload, dict):
        raise TrustError("信任文件根必须是对象")
    if payload.get("schema") != SCHEMA_TRUST:
        raise TrustError("信任文件 schema 必须是 %s" % SCHEMA_TRUST)
    allow = payload.get("allow") if isinstance(payload.get("allow"), dict) else {}
    rules: dict[str, list[str]] = {}
    for kind in RULE_KINDS:
        values = allow.get(kind)
        if values is None:
            rules[kind] = []
            continue
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise TrustError("allow.%s 必须是字符串数组" % kind)
        cleaned = [v.strip() for v in values if v.strip()]
        for value in cleaned:
            if kind == "pinned_manifest_sha256":
                digest, _, commit = value.lower().partition(":")
                if not re.match(SHA64_RE, digest):
                    raise TrustError("allow.pinned_manifest_sha256 含非 64 位摘要: %s" % value[:12])
                if commit and not re.match(SHA40_RE, commit):
                    raise TrustError("摘要钉的 commit 部分必须是 40 位 SHA: %s" % value[:20])
            if kind == "pinned_commit" and not re.match(SHA40_RE, value.lower()):
                raise TrustError("allow.pinned_commit 含非 40 位 SHA: %s" % value[:12])
        rules[kind] = [v.lower() for v in cleaned] if kind != "signed_commit_fingerprints" else cleaned
    return TrustConfig(path=str(p), rules=rules, raw=payload)


def evaluate_manifest(
    trust: TrustConfig,
    *,
    manifest_sha256: str,
    manifest_commit: str | None,
    manifest_signature: dict | None,
) -> TrustDecision:
    """只看清单本身的信任：摘要钉、清单提交钉、清单提交的签名。

    这里**不接受任务 commit**。任务的签名也不能替清单授权 —— 这是 r2 修的缺陷：
    以前调用方把 published[0].task_commit 传进来，钉住任一任务就放行了整份清单。
    """
    if not trust.configured:
        return TrustDecision(False, None, ["本地信任规则未配置（allow 为空）：真实自动执行被禁止"])

    manifest_sha256 = (manifest_sha256 or "").lower()
    manifest_commit = (manifest_commit or "").lower()

    pinned_manifests = trust.rules.get("pinned_manifest_sha256") or []
    pinned_commits = trust.rules.get("pinned_commit") or []

    # 协议要求（docs/AUTOMATION_PROTOCOL.md「信任」）：摘要钉必须绑定到具体 commit，
    # 不能只因为正文摘要相同就放行。两种写法：
    #   "<sha256>:<commit>"  摘要 + 提交绑定，两者必须同时命中
    #   "<sha256>"           裸摘要，仅当清单提交也在 pinned_commit 中才成立
    unbound_reason = ""
    for entry in pinned_manifests:
        digest, _, bound_commit = entry.partition(":")
        if digest != manifest_sha256:
            continue
        if bound_commit:
            if manifest_commit and bound_commit == manifest_commit:
                return TrustDecision(True, "pinned_manifest_sha256:bound", [], scope="manifest")
            unbound_reason = "摘要命中但绑定提交不匹配（钉 %s / 实际 %s）" % (
                bound_commit[:12], (manifest_commit or "未知")[:12])
        elif manifest_commit and manifest_commit in pinned_commits:
            return TrustDecision(True, "pinned_manifest_sha256+commit", [], scope="manifest")
        else:
            unbound_reason = "摘要命中但未绑定到具体 commit（需同时钉 pinned_commit 或用 <sha256>:<commit>）"

    if manifest_commit and manifest_commit in pinned_commits:
        return TrustDecision(True, "pinned_commit:manifest", [], scope="manifest")

    fingerprints = [f.replace(" ", "").lower()
                    for f in (trust.rules.get("signed_commit_fingerprints") or [])]
    if fingerprints and manifest_signature:
        status = manifest_signature.get("status")
        fp = (manifest_signature.get("fingerprint") or "").replace(" ", "").lower()
        if status == "good" and fp and fp in fingerprints:
            return TrustDecision(True, "signed_manifest_commit", [], scope="manifest")

    reasons = ["清单摘要、清单提交 SHA、清单提交签名均不匹配本机信任规则"]
    if unbound_reason:
        reasons.insert(0, unbound_reason)
    if manifest_signature is not None:
        reasons.append("清单提交签名状态=%s" % manifest_signature.get("status"))
    return TrustDecision(False, None, reasons)


def evaluate_task(
    trust: TrustConfig,
    *,
    task_commit: str,
    manifest_decision: TrustDecision,
) -> TrustDecision:
    """单个任务是否可执行。

    - 清单级已信任（摘要钉/清单提交钉/清单签名）→ 该清单内所有任务放行。
    - 否则只认「钉住的任务 commit」：只放行 task_commit 等于该钉的那一个任务。
    - 任务 commit 的签名不参与授权（签名只核清单提交）。
    """
    if manifest_decision.trusted:
        return TrustDecision(True, manifest_decision.rule, [], scope="manifest")

    commit = (task_commit or "").lower()
    pinned_commits = trust.rules.get("pinned_commit") or []
    if commit and commit in pinned_commits:
        return TrustDecision(True, "pinned_commit:task", [], scope="task", task_commit=commit)

    return TrustDecision(
        False, None,
        ["任务 commit 未被本机信任规则单独钉住，且清单级信任不成立"],
        scope="none", task_commit=commit or None,
    )


# 兼容旧调用名：只保留清单级语义，不再接受 task_commit。
def evaluate(trust: TrustConfig, **_kwargs) -> TrustDecision:
    raise TrustError("evaluate() 只做清单级判断，请改用 evaluate_manifest()/evaluate_task()")
