"""持久化台账（append-only JSONL）。

规则：
- 同一 (task_id, revision) 只允许一次 claim；终态之后不得重跑。
- 崩溃后只能由 recovery_required 交人核查，不得自动续跑。
- 台账是唯一事实来源；派生状态一律从台账重放，不另存“进度文件”。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .common import SCHEMA_LEDGER, append_jsonl_fsync, ensure_dir, now_iso

# 终态：出现其中任意一个，该 attempt 不再执行。
TERMINAL = frozenset(
    {
        "attempt_upload_ok",
        "attempt_abandoned",
        "attempt_refused_scope",
        "attempt_refused_trust",
        "attempt_refused_integrity",
        "attempt_failed",
        "attempt_quarantined",
    }
)
# 非终态但“不得重跑”：需要人工核查。
NEEDS_REVIEW = frozenset({"attempt_recovery_required", "attempt_cancelled"})

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_LOCKED = 3
EXIT_STOPPED = 4
EXIT_RECOVERY = 5
EXIT_ERROR = 6

# 协议只允许这六个台账状态（docs/AUTOMATION_PROTOCOL.md「台账」）。
PROTOCOL_STATES = ("accepted", "running", "succeeded", "failed", "stopped", "recovery_required")

# 本机细粒度事件 -> 协议状态。回执里要原样给出这张映射。
STATE_MAP: dict[str, str] = {
    "claim": "accepted",
    "attempt_start": "running",
    "attempt_phase": "running",              # phase=accepted/executing 都算 running，见 attempt_phase.phase
    "attempt_result_saved": "running",       # 回执已落盘、尚未上传，本次尝试还没收尾
    "attempt_upload_failed": "running",
    "attempt_upload_ok": "succeeded",
    "upload_duplicate_skipped": "succeeded",
    "attempt_failed": "failed",
    "attempt_quarantined": "failed",
    "attempt_refused_scope": "failed",
    "attempt_refused_integrity": "failed",
    "attempt_aborted_before_execution": "failed",
    "attempt_abandoned": "failed",
    "attempt_cancelled": "stopped",
    "upload_deferred_by_stop": "stopped",
    "attempt_recovery_required": "recovery_required",
}


def attempt_key(task_id: str, revision: int) -> str:
    return "%s@r%d" % (task_id, revision)


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._seq = 0
        self._records: list[dict[str, Any]] = []

    # ---------- 读 ----------
    def load(self) -> None:
        self._records = []
        self._seq = 0
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    # 崩溃可能留下半行；忽略尾部坏行，不猜测其含义。
                    continue
                if isinstance(record, dict):
                    self._records.append(record)
                    seq = record.get("seq")
                    if isinstance(seq, int) and seq > self._seq:
                        self._seq = seq

    @property
    def records(self) -> list[dict[str, Any]]:
        return list(self._records)

    # ---------- 写 ----------
    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        ensure_dir(self.path.parent)
        self._seq += 1
        record = {
            "schema": SCHEMA_LEDGER,
            "seq": self._seq,
            "ts": now_iso(),
            "pid": os.getpid(),
            "event": event,
        }
        record.update(fields)
        append_jsonl_fsync(self.path, record)
        self._records.append(record)
        return record

    # ---------- 派生 ----------
    def attempts(self) -> dict[str, dict[str, Any]]:
        """按 attempt_key 汇总最后状态。"""
        out: dict[str, dict[str, Any]] = {}
        for record in self._records:
            key = record.get("attempt")
            if not key:
                continue
            slot = out.setdefault(
                key,
                {
                    "attempt": key,
                    "task_id": record.get("task_id"),
                    "revision": record.get("revision"),
                    "digest": None,
                    "events": [],
                    "last": None,
                },
            )
            slot["events"].append(record.get("event"))
            slot["last"] = record.get("event")
            if record.get("digest"):
                slot["digest"] = record.get("digest")
            if record.get("task_id"):
                slot["task_id"] = record.get("task_id")
            if record.get("revision") is not None:
                slot["revision"] = record.get("revision")
        return out

    def state_of(self, key: str) -> str | None:
        slot = self.attempts().get(key)
        return slot["last"] if slot else None

    def protocol_state(self, key: str) -> str | None:
        """把本机事件名映射到协议六状态之一。"""
        slot = self.attempts().get(key)
        if not slot:
            return None
        for event in reversed(slot["events"]):
            if event in STATE_MAP:
                if event == "attempt_phase":
                    continue  # phase 细节由 attempt_phase 记录里的 phase 字段决定，仍算 running
                return STATE_MAP[event]
        return None

    def events_for(self, key: str) -> list[str]:
        slot = self.attempts().get(key)
        return list(slot["events"]) if slot else []

    def has_event_any(self, key: str, names) -> bool:
        events = set(self.events_for(key))
        return any(name in events for name in names)

    def has_claim(self, key: str) -> bool:
        """只要领取过就不得再次执行（同一编号+版本只跑一次）。"""
        return "claim" in self.events_for(key)

    def is_closed(self, key: str) -> bool:
        state = self.state_of(key)
        return state in TERMINAL or state in NEEDS_REVIEW

    def needs_review(self, key: str) -> bool:
        return self.state_of(key) in NEEDS_REVIEW

    def digest_of(self, key: str) -> str | None:
        slot = self.attempts().get(key)
        return slot.get("digest") if slot else None

    def by_task(self, task_id: str) -> list[dict[str, Any]]:
        return [r for r in self._records if r.get("task_id") == task_id]

    def stopped_flag(self) -> bool:
        """台账层记录的停止状态（跨重启保留）。"""
        return any(r.get("event") == "worker_stopped" for r in self._records) and not any(
            r.get("event") == "worker_resumed" for r in self._records
        )

    def summary(self) -> dict[str, Any]:
        attempts = self.attempts()
        closed = {k: v["last"] for k, v in attempts.items() if v["last"] in TERMINAL}
        review = {k: v["last"] for k, v in attempts.items() if v["last"] in NEEDS_REVIEW}
        uploaded = [k for k, v in attempts.items() if v["last"] == "attempt_upload_ok"]
        states = {k: self.protocol_state(k) for k in attempts}
        return {
            "records": len(self._records),
            "attempts": len(attempts),
            "closed": closed,
            "needs_review": review,
            "uploaded": uploaded,
            "protocol_states": states,
            "last_events": [r.get("event") for r in self._records[-8:]],
        }
