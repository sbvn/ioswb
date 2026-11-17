"""持久 handoff 与 context 预算。

协议要求（docs/AUTOMATION_PROTOCOL.md「执行方式」）：
- 每个任务使用新的独立会话；
- 会话可以换新，交接状态要能跨过本次尝试保存。

因此 handoff 落在本机磁盘（`state/handoff/<task_id>.json`），不是会话内存；
下一次尝试（可能是新 revision、新进程）启动时先读它，再把摘要放进新会话的上下文。
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import SCHEMA_HANDOFF, atomic_write_text, ensure_dir, now_iso

MAX_HISTORY = 8


def _compact(record: dict | None) -> str:
    if not record:
        return "(无历史交接)"
    keep = {
        "task_id": record.get("task_id"),
        "revision": record.get("revision"),
        "attempt": record.get("attempt"),
        "phase": record.get("phase"),
        "digest": (record.get("digest") or "")[:16],
        "summary": record.get("summary"),
        "updated_at": record.get("updated_at"),
        "receipt_rel_path": (record.get("artifacts") or {}).get("receipt_rel_path"),
        "ledger_seq": (record.get("artifacts") or {}).get("ledger_seq"),
    }
    return json.dumps(keep, ensure_ascii=False, sort_keys=True)


class HandoffStore:
    """按 task_id 持久化的交接记录（跨尝试、跨进程）。"""

    def __init__(self, root: Path, task_id: str) -> None:
        self.dir = root
        self.task_id = task_id
        self.path = root / ("%s.json" % task_id)

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
        return payload if isinstance(payload, dict) else None

    def save(self, *, revision: int, attempt: int, phase: str, digest: str,
             summary: str, receipt_rel_path: str | None = None,
             ledger_seq: int | None = None) -> dict:
        ensure_dir(self.dir)
        previous = self.load() or {}
        history = list(previous.get("history") or [])
        if previous.get("phase"):
            history.append({
                "revision": previous.get("revision"),
                "attempt": previous.get("attempt"),
                "phase": previous.get("phase"),
                "updated_at": previous.get("updated_at"),
            })
        record = {
            "schema": SCHEMA_HANDOFF,
            "task_id": self.task_id,
            "revision": revision,
            "attempt": attempt,
            "phase": phase,
            "digest": digest,
            "summary": summary,
            "updated_at": now_iso(),
            "artifacts": {
                "receipt_rel_path": receipt_rel_path or (previous.get("artifacts") or {}).get("receipt_rel_path"),
                "ledger_seq": ledger_seq,
            },
            "history": history[-MAX_HISTORY:],
        }
        atomic_write_text(self.path, json.dumps(record, ensure_ascii=False, indent=2))
        return record


def compose_context(task_text: str, handoff: dict | None, budget_bytes: int) -> tuple[str, dict]:
    """把 handoff 摘要与任务正文拼成一次新会话的输入，并强制 context 预算。

    返回 (prompt_text, meta)。预算按 UTF-8 字节计；超预算时截断任务正文并留下显式标记，
    绝不静默丢弃。
    """
    header = (
        "你在无人值守模式下执行一份已发布的任务单。这是**新的独立会话**，"
        "上一次尝试的状态以 HANDOFF 形式给出。\n"
    )
    handoff_block = "\n----- HANDOFF（上一次尝试，可能为空）-----\n%s\n" % _compact(handoff)
    footer = (
        "\n硬性约束：只做任务单范围内的事；不连接手机、不注册、不采集凭据、不安装工具；"
        "回执必须脱敏；不要执行 git push。\n"
        "把最终回执同时写入当前目录的 RECEIPT.md（Markdown，脱敏），然后结束。\n"
        "----- 任务单开始 -----\n"
    )
    fixed = len((header + handoff_block + footer + "\n----- 任务单结束 -----\n").encode("utf-8"))
    task_bytes = task_text.encode("utf-8")
    available = max(0, budget_bytes - fixed)
    truncated = len(task_bytes) > available
    marker_reserve = 200  # 给截断标记本身预留，保证 prompt 不超预算
    if truncated:
        cut = max(0, available - marker_reserve)
        body = task_bytes[:cut].decode("utf-8", errors="ignore")
        body += ("\n\n… [任务正文因 context 预算被截断：原文 %d 字节，保留 %d 字节，预算 %d 字节] …\n"
                 % (len(task_bytes), cut, budget_bytes))
    else:
        body = task_text
    prompt = header + handoff_block + footer + body + "\n----- 任务单结束 -----\n"
    prompt_bytes = len(prompt.encode("utf-8"))
    meta = {
        "budget_bytes": budget_bytes,
        "prompt_bytes": prompt_bytes,
        "task_bytes": len(task_bytes),
        "kept_task_bytes": len(body.encode("utf-8")),
        "trimmed": truncated,
        "within_budget": prompt_bytes <= budget_bytes,
        "handoff_present": bool(handoff),
        "handoff_phase": (handoff or {}).get("phase"),
    }
    return prompt, meta
