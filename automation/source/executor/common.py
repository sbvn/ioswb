"""IOSWB 自动任务执行器 —— 公共工具。

只允许写 automation/ 下的运行目录；不触碰业务脚本与设备。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA_CONFIG = "ioswb-automation-config/1"
SCHEMA_MANIFEST = "ioswb-release-manifest/1"
SCHEMA_TRUST = "ioswb-trust/1"
SCHEMA_LEDGER = "ioswb-automation-ledger/1"
SCHEMA_ATTEMPT = "ioswb-attempt/1"
SCHEMA_HANDOFF = "ioswb-handoff/1"

TZ_HK = timezone(timedelta(hours=8))

# 允许的自动化能力范围（默认只放开交接框架与离线测试）。
SCOPE_ALLOWED_DEFAULT = ("framework-development", "offline-testing")
SCOPE_DENIED_ALWAYS = (
    "phone-operation",
    "device-attach",
    "real-touch",
    "spawn",
    "kill",
    "registration",
    "credential-capture",
    "tool-install",
    "batch-run",
    "publish-task",
)

TASK_ID_RE = r"^[A-Z][A-Z0-9]{1,11}-\d{3}$"
SHA40_RE = r"^[0-9a-f]{40}$"
SHA64_RE = r"^[0-9a-f]{64}$"


class AutomationError(Exception):
    """所有执行器错误的基类。"""


class ConfigError(AutomationError):
    pass


class GitError(AutomationError):
    pass


class ManifestError(AutomationError):
    pass


class TrustError(AutomationError):
    pass


class ScopeError(AutomationError):
    pass


def now_iso() -> str:
    return datetime.now(TZ_HK).isoformat(timespec="seconds")


def now_epoch() -> float:
    import time

    return time.time()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json_file(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


def _fsync_dir(path: Path) -> None:
    """尽最大努力 fsync 目录（Windows 不支持，忽略）。"""
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """同目录临时文件 + fsync + os.replace，保证读到的要么是旧内容要么是新内容。"""
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def append_jsonl_fsync(path: Path, record: dict) -> None:
    """追加一行 JSON 并 fsync；台账不允许出现半行以外的不一致。"""
    ensure_dir(path.parent)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def safe_relpath(value: str) -> str:
    """校验并归一化仓库内相对路径：禁止绝对路径、禁止 .. 逃逸。"""
    raw = (value or "").replace("\\", "/").strip()
    if not raw:
        raise ValueError("空路径")
    if raw.startswith("/") or (len(raw) > 2 and raw[1] == ":"):
        raise ValueError("禁止绝对路径: %s" % value)
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("禁止路径逃逸: %s" % value)
    return "/".join(parts)


def mask_secret(value: str, keep: int = 4) -> str:
    value = value or ""
    if len(value) <= keep:
        return "***"
    return value[:keep] + "***"
