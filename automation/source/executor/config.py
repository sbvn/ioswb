"""执行器配置。

默认 dry-run；mock 只允许指向本机路径；live 需要多重闸门同时成立。
配置错误一律 fail-closed。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .common import (
    SCHEMA_CONFIG,
    ConfigError,
    SCOPE_ALLOWED_DEFAULT,
    SCOPE_DENIED_ALWAYS,
    ensure_dir,
    read_json_file,
)

MODES = ("dry-run", "mock", "live")


@dataclass
class Limits:
    max_attempts_per_revision: int = 1
    upload_retries: int = 3
    task_timeout_seconds: float = 3600.0
    cancel_grace_seconds: float = 10.0
    scan_inflight_seconds: float = 5.0
    context_budget_bytes: int = 48000


@dataclass
class HarnessConfig:
    kind: str = "dsh-headless"
    enabled: bool = False
    product_version_allow: tuple[str, ...] = ()
    permission_mode: str = "workspace-write"
    approval_policy: str = "never"
    timeout_seconds: float = 3600.0
    mock_command: tuple[str, ...] = ()
    mock_enabled: bool = True
    documented: tuple[str, ...] = ()


@dataclass
class Config:
    path: Path
    root: Path
    mode: str
    repo_url: str
    repo_branch: str
    manifest_path: str
    pause_flag_path: str
    results_root: str
    allow_main_fallback: bool
    poll_interval_seconds: float
    allowed_scopes: tuple[str, ...]
    denied_scopes: tuple[str, ...]
    limits: Limits
    harness: HarnessConfig
    live_enabled: bool
    live_blocked_reason: str
    trust_file: Path
    raw: dict[str, Any] = field(default_factory=dict)

    # ---------- 路径 ----------
    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def outbox_dir(self) -> Path:
        return self.root / "outbox"

    @property
    def work_dir(self) -> Path:
        return self.state_dir / "work"

    @property
    def quarantine_dir(self) -> Path:
        return self.state_dir / "quarantine"

    @property
    def attempts_dir(self) -> Path:
        return self.state_dir / "attempts"

    @property
    def handoff_dir(self) -> Path:
        return self.state_dir / "handoff"

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "ledger.jsonl"

    @property
    def lock_path(self) -> Path:
        return self.state_dir / "worker.lock"

    @property
    def stop_path(self) -> Path:
        return self.state_dir / "STOP"

    @property
    def heartbeat_path(self) -> Path:
        return self.state_dir / "heartbeat.json"

    @property
    def worker_state_path(self) -> Path:
        return self.state_dir / "worker.json"

    def ensure_dirs(self) -> None:
        for path in (self.state_dir, self.outbox_dir, self.work_dir,
                     self.quarantine_dir, self.attempts_dir, self.handoff_dir):
            ensure_dir(path)

    def result_rel_path(self, task_id: str, revision: int, attempt: int) -> str:
        return "%s/%s/r%d/a%d.md" % (self.results_root, task_id, revision, attempt)


def _as_str_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise ConfigError("%s 必须是字符串数组" % field_name)
    return [v.strip() for v in value]


def load_config(path: str | Path) -> Config:
    p = Path(path).resolve()
    if not p.exists():
        raise ConfigError("配置文件不存在: %s" % p)
    try:
        raw = read_json_file(p)
    except Exception as exc:  # noqa: BLE001
        raise ConfigError("配置文件不是合法 JSON: %s" % exc) from exc
    if not isinstance(raw, dict):
        raise ConfigError("配置根必须是对象")
    if raw.get("schema") != SCHEMA_CONFIG:
        raise ConfigError("配置 schema 必须是 %s" % SCHEMA_CONFIG)

    mode = str(raw.get("mode") or "").strip()
    if mode not in MODES:
        raise ConfigError("mode 必须是 %s 之一，实际 %r" % ("/".join(MODES), mode))

    repo = raw.get("repo") or {}
    if not isinstance(repo, dict):
        raise ConfigError("repo 必须是对象")
    url = str(repo.get("url") or "").strip()
    branch = str(repo.get("branch") or "").strip()
    if not url or not branch:
        raise ConfigError("repo.url 与 repo.branch 必填")
    manifest_path = str(repo.get("manifest_path") or "manifest/releases.json").strip()
    pause_flag_path = str(repo.get("pause_flag_path") or "manifest/PAUSE").strip()
    results_root = str(repo.get("results_root") or "results").strip()

    poll = raw.get("poll") or {}
    if not isinstance(poll, dict):
        raise ConfigError("poll 必须是对象")
    interval = float(poll.get("interval_seconds", 60))
    if interval < 5:
        raise ConfigError("poll.interval_seconds 至少 5 秒")

    scope = raw.get("scope") or {}
    if not isinstance(scope, dict):
        raise ConfigError("scope 必须是对象")
    allowed = tuple(_as_str_list(scope.get("allowed"), "scope.allowed")) or SCOPE_ALLOWED_DEFAULT
    denied_extra = tuple(_as_str_list(scope.get("denied_overrides"), "scope.denied_overrides"))
    denied = tuple(dict.fromkeys(list(SCOPE_DENIED_ALWAYS) + list(denied_extra)))

    limits_raw = raw.get("limits") or {}
    if not isinstance(limits_raw, dict):
        raise ConfigError("limits 必须是对象")
    limits = Limits(
        max_attempts_per_revision=int(limits_raw.get("max_attempts_per_revision", 1)),
        upload_retries=int(limits_raw.get("upload_retries", 3)),
        task_timeout_seconds=float(limits_raw.get("task_timeout_seconds", 3600.0)),
        cancel_grace_seconds=float(limits_raw.get("cancel_grace_seconds", 10.0)),
        scan_inflight_seconds=float(limits_raw.get("scan_inflight_seconds", 5.0)),
        context_budget_bytes=int(limits_raw.get("context_budget_bytes", 48000)),
    )
    if limits.context_budget_bytes < 2048:
        raise ConfigError("limits.context_budget_bytes 至少 2048")

    harness_raw = raw.get("harness") or {}
    if not isinstance(harness_raw, dict):
        raise ConfigError("harness 必须是对象")
    unattended = harness_raw.get("unattended") or {}
    mock_raw = harness_raw.get("mock") or {}
    if not isinstance(unattended, dict) or not isinstance(mock_raw, dict):
        raise ConfigError("harness.unattended / harness.mock 必须是对象")
    harness = HarnessConfig(
        kind=str(unattended.get("kind") or "dsh-headless"),
        enabled=bool(unattended.get("enabled", False)),
        product_version_allow=tuple(_as_str_list(unattended.get("product_version_allow"),
                                                 "harness.unattended.product_version_allow")),
        permission_mode=str(unattended.get("permission_mode") or "workspace-write"),
        approval_policy=str(unattended.get("approval_policy") or "never"),
        timeout_seconds=float(unattended.get("timeout_seconds", 3600.0)),
        mock_command=tuple(_as_str_list(mock_raw.get("command"), "harness.mock.command")),
        mock_enabled=bool(mock_raw.get("enabled", True)),
        documented=tuple(_as_str_list(unattended.get("documented"), "harness.unattended.documented")),
    )

    live_raw = raw.get("live") or {}
    if not isinstance(live_raw, dict):
        raise ConfigError("live 必须是对象")
    live_enabled = bool(live_raw.get("enabled", False))
    live_blocked_reason = str(live_raw.get("reason") or "").strip()

    trust_file_value = str(raw.get("trust_file") or "trust/publishers.json").strip()
    trust_file = (p.parent / trust_file_value).resolve()

    root = p.parent.parent.resolve()
    cfg = Config(
        path=p,
        root=root,
        mode=mode,
        repo_url=url,
        repo_branch=branch,
        manifest_path=manifest_path,
        pause_flag_path=pause_flag_path,
        results_root=results_root,
        allow_main_fallback=bool(repo.get("allow_main_fallback", False)),
        poll_interval_seconds=interval,
        allowed_scopes=allowed,
        denied_scopes=denied,
        limits=limits,
        harness=harness,
        live_enabled=live_enabled,
        live_blocked_reason=live_blocked_reason,
        trust_file=trust_file,
        raw=raw,
    )
    _validate_placement(cfg)
    _validate_mode(cfg)
    return cfg


def _validate_placement(cfg: Config) -> None:
    """运行目录必须落在 automation 根下，避免写业务目录。"""
    root = cfg.root.resolve()
    for path in (cfg.state_dir.resolve(), cfg.outbox_dir.resolve(), cfg.work_dir.resolve()):
        if root != path and root not in path.parents:
            raise ConfigError("运行目录必须位于 automation 根目录内: %s" % path)
    if cfg.allow_main_fallback:
        raise ConfigError("不允许 main 回退（allow_main_fallback 必须为 false）")
    if cfg.repo_branch == "main":
        raise ConfigError("默认分支不得为 main；必须显式指定协作分支")


def _is_local_url(url: str) -> bool:
    lowered = url.lower()
    if lowered.startswith("file://"):
        return True
    if lowered.startswith(("http://", "https://", "ssh://", "git@", "git://")):
        return False
    return True  # 纯路径


def _validate_mode(cfg: Config) -> None:
    if cfg.mode == "mock":
        if not _is_local_url(cfg.repo_url):
            raise ConfigError("mock 模式只允许本机路径或 file:// 远端，禁止指向真实远端")
        if not cfg.harness.mock_enabled:
            raise ConfigError("mock 模式需要 harness.mock.enabled=true")
        if cfg.live_enabled:
            raise ConfigError("mock 模式下 live.enabled 必须为 false")
    if cfg.mode == "live":
        problems = []
        if not cfg.live_enabled:
            problems.append("live.enabled=false")
        if not cfg.harness.enabled:
            problems.append("harness.unattended.enabled=false")
        if not cfg.harness.product_version_allow:
            problems.append("未声明允许的 Harness 版本")
        if cfg.live_blocked_reason:
            problems.append(cfg.live_blocked_reason)
        try:
            trust_cfg = json.loads(cfg.trust_file.read_text(encoding="utf-8"))
            allow = (trust_cfg or {}).get("allow") or {}
            signers = (trust_cfg or {}).get("signers") or []
            if not any(allow.get(k) for k in ("pinned_manifest_sha256", "pinned_commit",
                                              "signed_commit_fingerprints")) and not signers:
                problems.append("本机信任规则未配置")
        except Exception:  # noqa: BLE001
            problems.append("信任文件缺失或不可读: %s" % cfg.trust_file)
        if problems:
            raise ConfigError("live 模式闸门未全部通过: " + "; ".join(problems))
