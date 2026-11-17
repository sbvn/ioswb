#!/usr/bin/env python3
"""公开的 final 事件故障注入。不调用模型，不读凭据。

旧实现：exit 0 且 final.text 非空就标 success，不看 reason.kind。
本探针断言：只有 exit 0、恰好一条 final、reason.kind 严格等于 completed、
且有非空任务输出时才是 success。其余 fail closed。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
AUTOMATION_ROOT = TESTS_DIR.parent
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from lab import Lab  # noqa: E402

MARKER = "IOS-AUTO-SMOKE-001\nSMOKE-001"

# 每条都是完整输入。expect 是 run() 的 status。
CASES = [
    {
        "name": "error_kind_with_text",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "error"}, "text": "看起来像答案"}],
        "expect": "failed",
        "error_has": "不是 completed",
    },
    {
        "name": "aborted_kind_with_text",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "aborted"}, "text": MARKER}],
        "expect": "failed",
        "error_has": "不是 completed",
    },
    {
        "name": "cancelled_kind_with_text",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "cancelled"}, "text": MARKER}],
        "expect": "failed",
        "error_has": "不是 completed",
    },
    {
        "name": "missing_reason",
        "exit": 0,
        "events": [{"type": "final", "text": MARKER}],
        "expect": "failed",
        "error_has": "缺少 reason",
    },
    {
        "name": "null_reason",
        "exit": 0,
        "events": [{"type": "final", "reason": None, "text": MARKER}],
        "expect": "failed",
        "error_has": "缺少 reason",
    },
    {
        "name": "kind_not_exactly_completed",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "Completed"}, "text": MARKER}],
        "expect": "failed",
        "error_has": "不是 completed",
    },
    {
        "name": "no_final",
        "exit": 0,
        "events": [{"type": "session", "sessionId": "session-x"}],
        "expect": "failed",
        "error_has": "无 final",
    },
    {
        "name": "bad_json",
        "exit": 0,
        "raw": "{\"type\":\"session\"}\nnot-json\n",
        "expect": "failed",
        "error_has": "格式坏",
    },
    {
        "name": "two_finals_disagree",
        "exit": 0,
        "events": [
            {"type": "final", "reason": {"kind": "completed"}, "text": MARKER},
            {"type": "final", "reason": {"kind": "error"}, "text": "另一份"},
        ],
        "expect": "failed",
        "error_has": "歧义",
    },
    {
        "name": "two_identical_finals",
        "exit": 0,
        "events": [
            {"type": "final", "reason": {"kind": "completed"}, "text": MARKER},
            {"type": "final", "reason": {"kind": "completed"}, "text": MARKER},
        ],
        "expect": "failed",
        "error_has": "歧义",
    },
    {
        "name": "empty_text",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "completed"}, "text": "  \n"}],
        "expect": "failed",
        "error_has": "没有有效任务输出",
    },
    {
        "name": "nonzero_exit_even_if_completed",
        "exit": 1,
        "events": [{"type": "final", "reason": {"kind": "completed"}, "text": MARKER}],
        "expect": "failed",
    },
    {
        "name": "receipt_cannot_override_error",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "error"}, "text": "看起来像答案"}],
        "receipt": MARKER,
        "expect": "failed",
        "error_has": "不是 completed",
    },
    {
        "name": "receipt_and_text_mismatch",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "completed"}, "text": MARKER}],
        "receipt": "别的输出",
        "expect": "failed",
        "error_has": "不一致",
    },
    {
        "name": "completed_with_marker",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "completed"}, "text": MARKER}],
        "expect": "success",
    },
    {
        "name": "completed_receipt_when_text_empty",
        "exit": 0,
        "events": [{"type": "final", "reason": {"kind": "completed"}, "text": ""}],
        "receipt": MARKER,
        "expect": "success",
    },
]


def _events_blob(case: dict) -> str:
    if "raw" in case:
        return case["raw"]
    return "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in case["events"])


def run_case(lab: Lab, stub: Path, case: dict):
    from executor.config import load_config
    from executor.runner import HeadlessRunner

    attempt = lab.root / "state" / "attempts" / case["name"]
    if attempt.exists():
        for child in attempt.iterdir():
            child.unlink()
    attempt.mkdir(parents=True, exist_ok=True)
    blob = attempt / "events.jsonl"
    blob.write_text(_events_blob(case), encoding="utf-8")
    receipt = attempt / "RECEIPT.md"
    if "receipt" in case:
        receipt.write_text(case["receipt"], encoding="utf-8")
    elif receipt.exists():
        receipt.unlink()
    os.environ["HEADLESS_STUB_EXIT"] = str(case["exit"])
    os.environ["HEADLESS_STUB_STDOUT"] = str(blob)
    runner = HeadlessRunner(
        load_config(lab.config_path),
        attempt,
        {"node_executable": sys.executable, "bin_js": str(stub)},
    )
    return runner.run({"context_text": "T", "task_text": "T"}, {}, timeout=5, should_cancel=lambda: False)


def main() -> int:
    lab = Lab("final_gate_probe")
    lab.write_config(mode="mock")
    stub = lab.root / "stub_headless.py"
    stub.write_text(
        "import os, sys\n"
        "path = os.environ.get('HEADLESS_STUB_STDOUT', '')\n"
        "if path:\n"
        "    with open(path, 'rb') as handle:\n"
        "        sys.stdout.buffer.write(handle.read())\n"
        "sys.exit(int(os.environ.get('HEADLESS_STUB_EXIT', '0')))\n",
        encoding="utf-8",
    )
    failed = 0
    for case in CASES:
        outcome = run_case(lab, stub, case)
        ok = outcome.status == case["expect"]
        if ok and case.get("error_has") and case["error_has"] not in (outcome.error or ""):
            ok = False
        if not ok:
            failed += 1
        print(json.dumps({
            "case": case["name"],
            "input": {
                "exit": case["exit"],
                "events": case.get("events"),
                "raw": case.get("raw"),
                "receipt": case.get("receipt"),
            },
            "expect": case["expect"],
            "actual": outcome.status,
            "error": outcome.error,
            "ok": ok,
        }, ensure_ascii=False))
    print("PROBE %d/%d" % (len(CASES) - failed, len(CASES)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
