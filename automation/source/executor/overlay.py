"""临时执行层。

磁盘上的 automation.json 保持 dry-run。持续入口只在内存里使用 mock，
并用 try/finally 清掉临时 patch。崩溃后下次启动先清残留，不会留下 live。
这里不写登录 patch，也不改 $DSH_HOME。
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from .config import Config


def marker_path(cfg: Config) -> Path:
    return cfg.state_dir / "overlay.json"


def scrub_overlay(cfg: Config) -> list[str]:
    """删掉上次未收干净的临时文件。不把配置改成 live。"""
    removed: list[str] = []
    path = marker_path(cfg)
    listed: list[str] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            raw = payload.get("patch_files") or []
            if isinstance(raw, list):
                listed = [str(item) for item in raw]
        path.unlink()
        removed.append(str(path))
    for item in listed:
        patch = Path(item)
        try:
            resolved = patch.resolve()
        except OSError:
            continue
        root = cfg.state_dir.resolve()
        if resolved != root and root not in resolved.parents:
            continue
        if resolved.exists() and resolved.is_file():
            resolved.unlink()
            removed.append(str(resolved))
    backup = cfg.state_dir / "config.backup.json"
    if backup.exists() and cfg.path.exists():
        cfg.path.write_bytes(backup.read_bytes())
        backup.unlink()
        removed.append(str(backup))
    return removed


@contextmanager
def execution_overlay(cfg: Config):
    """创建临时 patch 标记，退出时删除，并在配置被改写时还原字节。"""
    cfg.ensure_dirs()
    scrub_overlay(cfg)
    original = cfg.path.read_bytes()
    patch = cfg.state_dir / "overlay-empty.yml"
    patch.write_text("# temporary overlay\nsaved_login: false\n", encoding="utf-8")
    marker_path(cfg).write_text(json.dumps({
        "schema": "ioswb-overlay/1",
        "mode": "mock",
        "saved_login": False,
        "live": False,
        "patch_files": [str(patch)],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        yield {"mode": "mock", "patch": patch}
    finally:
        if patch.exists():
            patch.unlink()
        path = marker_path(cfg)
        if path.exists():
            path.unlink()
        if cfg.path.exists() and cfg.path.read_bytes() != original:
            cfg.path.write_bytes(original)
