"""操作员控制面：status / stop / resume / ack。

停止与恢复都是显式动作：
- stop 只创建 STOP 文件，不直接杀进程；运行中的 worker 自己取消子进程并等它退出。
- resume 必须带 --confirm，因为恢复会解除“跨重启保留”的停止状态。
- ack 只关闭“结果不明”的 attempt，绝不触发重新执行。
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .common import atomic_write_text, now_iso
from .config import Config
from .ledger import NEEDS_REVIEW, TERMINAL, Ledger
from .locking import lock_is_held


def _heartbeat_age(cfg: Config) -> float | None:
    if not cfg.heartbeat_path.exists():
        return None
    try:
        payload = json.loads(cfg.heartbeat_path.read_text(encoding="utf-8"))
        return max(0.0, time.time() - float(payload.get("epoch") or 0))
    except Exception:  # noqa: BLE001
        return None


def status(cfg: Config) -> dict:
    ledger = Ledger(cfg.ledger_path)
    ledger.load()
    attempts = ledger.attempts()
    age = _heartbeat_age(cfg)
    pending = []
    if cfg.outbox_dir.exists():
        ready = {"attempt_result_saved", "attempt_upload_failed", "upload_deferred_by_stop"}
        for key, slot in attempts.items():
            if slot["last"] not in ready:
                continue
            task_id = slot.get("task_id") or key.partition("@")[0]
            revision = slot.get("revision") or 1
            rel = cfg.result_rel_path(str(task_id), int(revision), 1)
            path = cfg.outbox_dir / rel
            if path.exists():
                pending.append(str(path.relative_to(cfg.root)))
    needs_review = sorted(k for k, v in attempts.items() if v["last"] in NEEDS_REVIEW)
    return {
        "mode": cfg.mode,
        "branch": cfg.repo_branch,
        "repo_url": cfg.repo_url,
        "config": str(cfg.path),
        "lock_held": lock_is_held(cfg.lock_path),
        "stop_file_present": cfg.stop_path.exists(),
        "stop_file": str(cfg.stop_path),
        "heartbeat_age_seconds": None if age is None else round(age, 1),
        "heartbeat_note": (
            "无心跳：worker 可能从未启动或已正常退出"
            if age is None else
            ("心跳较旧：仅提示，禁止据此抢锁或重跑；请先确认进程状态"
             if age > 180 else "心跳正常")
        ),
        "attempts": {k: {"last": v["last"], "protocol_state": ledger.protocol_state(k),
                         "digest": (v["digest"] or "")[:12]}
                     for k, v in sorted(attempts.items())},
        "handoff_files": sorted(str(p.relative_to(cfg.root)) for p in cfg.handoff_dir.glob("*.json"))
        if cfg.handoff_dir.exists() else [],
        "needs_review": needs_review,
        "pending_uploads": pending,
        "summary": ledger.summary(),
    }


def stop(cfg: Config, note: str = "") -> dict:
    cfg.ensure_dirs()
    payload = {"requested_at": now_iso(), "pid": os.getpid(), "note": note or "operator stop"}
    atomic_write_text(cfg.stop_path, json.dumps(payload, ensure_ascii=False, indent=2))
    ledger = Ledger(cfg.ledger_path)
    ledger.load()
    ledger.append("stop_requested", source="operator", note=note or "")
    return {
        "stop_file": str(cfg.stop_path),
        "instruction": "运行中的 worker 会在下一次检查点取消子进程并等待其退出；"
                       "只有在回执里看到 cancel_confirmed=true 才算停止成功。",
    }


def resume(cfg: Config, confirm: bool, note: str = "") -> dict:
    if not confirm:
        raise SystemExit("拒绝：恢复会解除跨重启保留的停止状态，必须显式加 --confirm。")
    if not cfg.stop_path.exists():
        return {"stop_file": str(cfg.stop_path), "removed": False, "note": "STOP 不存在"}
    cfg.stop_path.unlink()
    ledger = Ledger(cfg.ledger_path)
    ledger.load()
    ledger.append("worker_resumed", source="operator", note=note or "")
    return {"stop_file": str(cfg.stop_path), "removed": True}


def ack(cfg: Config, attempt: str, decision: str, note: str) -> dict:
    ledger = Ledger(cfg.ledger_path)
    ledger.load()
    state = ledger.state_of(attempt)
    if state is None:
        raise SystemExit("未知 attempt: %s" % attempt)
    if state in TERMINAL:
        return {"attempt": attempt, "state": state, "note": "已是终态，无需 ack"}
    ledger.append("attempt_abandoned", attempt=attempt, decision=decision or "abandoned",
                  ack_by="operator", ack_note=note or "",
                  note="人工核查后关闭；不会触发重跑，如需继续请发布新 revision")
    return {"attempt": attempt, "state": "attempt_abandoned", "decision": decision or "abandoned"}
