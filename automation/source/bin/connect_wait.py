#!/usr/bin/env python3
"""一次连接的独立等待器（标准库，不调用模型）。

依据：`automation/CONNECT_ONCE.md` 的「等待器」节与 `tasks/AUTO-CONNECT-001.md` 的门禁第 4-6 条。

职责：
- 每 60 秒只读扫描唯一 ref `cursor/init-collab-docs-2e45` 的 TASKS.md、reviews/、manifest/releases.json。
- 台账持久化在本机 `automation/state/connect/`，跨重启保留。
- 扫描失败按 60/120/240 … 退避，最长 15 分钟；退避不是退出。
- 只做观察与记录，不执行任务、不调用 headless、不写 `manifest/releases.json`、不碰信任配置。

用法：
  py -3.12 automation/bin/connect_wait.py --once
  py -3.12 automation/bin/connect_wait.py --interval 60 --cycles 0
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # automation/
STATE = ROOT / "state" / "connect"
STATUS = STATE / "status.json"
LEDGER = STATE / "scan.jsonl"
HANDOFF = ROOT / "state" / "handoff" / "AUTO-CONNECT-001.json"

REF = "cursor/init-collab-docs-2e45"
REMOTE = "https://github.com/sbvn/ioswb.git"
WATCH = ("TASKS.md", "reviews", "manifest/releases.json")
MAX_BACKOFF = 900.0


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def ensure_state() -> None:
    STATE.mkdir(parents=True, exist_ok=True)


def read_status() -> dict:
    if STATUS.exists():
        try:
            return json.loads(STATUS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_status(payload: dict) -> None:
    ensure_state()
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS)


def append_ledger(record: dict) -> None:
    ensure_state()
    with open(LEDGER, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def git(args: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess:
    import os

    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return subprocess.run(["git"] + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env)


def _refresh_ref() -> Path:
    """把唯一 ref 的 HEAD 浅浅拉到本机，供只读扫描使用（不写远端）。"""
    clone_dir = STATE / "ref"
    if not (clone_dir / ".git").exists():
        git(["clone", "--quiet", "--depth", "1", "--branch", REF, REMOTE, str(clone_dir)],
            timeout=300)
    else:
        git(["-C", str(clone_dir), "fetch", "--quiet", "--depth", "1", "origin", REF],
            timeout=300)
        git(["-C", str(clone_dir), "reset", "--quiet", "--hard", "FETCH_HEAD"], timeout=120)
    return clone_dir


def scan() -> dict:
    """只读扫描：远端分支头 + TASKS.md 关键行 + reviews 列表 + 清单是否存在。"""
    head = git(["ls-remote", "--heads", REMOTE, REF], timeout=60)
    if head.returncode != 0:
        raise RuntimeError((head.stderr or head.stdout).strip()[:300])
    remote_commit = (head.stdout.split() or [""])[0]
    if not remote_commit:
        raise RuntimeError("远端没有该 ref")

    clone_dir = _refresh_ref()
    commit = git(["-C", str(clone_dir), "rev-parse", "HEAD"], timeout=60).stdout.strip()
    files = sorted(str(p.relative_to(clone_dir)).replace("\\", "/")
                   for p in clone_dir.rglob("*") if p.is_file() and ".git" not in p.parts)
    tasks_path = clone_dir / "TASKS.md"
    tasks_md = tasks_path.read_text(encoding="utf-8", errors="replace") if tasks_path.exists() else ""

    reviews = [f for f in files if f.startswith("reviews/") and f.endswith(".md")]
    results = [f for f in files if f.startswith("results/") and f.endswith(".md")]
    r2_receipt = "results/IOS-002/r2/a1.md" in files
    r2_review = [r for r in reviews if "IOS-002-r2" in r.lower() or "r2" in r.lower()
                 and "IOS-002" in r]
    r2_row = [line.strip() for line in tasks_md.splitlines()
              if line.strip().startswith("| IOS-002") and "r2" in line]
    return {
        "commit": commit or remote_commit,
        "r2_receipt_present": r2_receipt,
        "r2_reviews": r2_review,
        "manifest_present": "manifest/releases.json" in files,
        "r2_task_row": r2_row[:1],
        "reviews": reviews,
        "results": results,
    }


def decide_phase(snap: dict) -> tuple[str, str]:
    """返回 (阶段, 阻塞方)。只做判断，不执行任务。"""
    if snap["r2_reviews"]:
        return "3", "01 已出 r2 验收；下一步等 01 另发受控 smoke 与用户外带确认"
    if snap["r2_receipt_present"]:
        return "2", "01 的 review"
    return "1", "Harness 执行（r2 尚未提交回执）"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AUTO-CONNECT-001 只读等待器")
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--cycles", type=int, default=0, help="0 表示不限")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    ensure_state()
    previous = read_status()
    restart_note = ""
    if previous.get("running"):
        restart_note = "上次已退出（进程不在），之前不是常驻"
    status = {
        "schema": "ioswb-connect-status/1",
        "pid": __import__("os").getpid(),
        "started_at": previous.get("started_at") or now(),
        "running": True,
        "restart_note": restart_note,
        "ref": REF,
        "phase": previous.get("phase", "1"),
        "blocker": previous.get("blocker", "Harness 执行"),
        "last_scan_at": previous.get("last_scan_at"),
        "last_commit": previous.get("last_commit"),
        "consecutive_failures": int(previous.get("consecutive_failures") or 0),
        "next_backoff_seconds": 0,
    }
    write_status(status)
    append_ledger({"ts": now(), "event": "waiter_start", "restart_note": restart_note,
                   "phase": status["phase"]})

    cycles = 0
    backoff = args.interval
    try:
        while True:
            cycles += 1
            try:
                snap = scan()
                phase, blocker = decide_phase(snap)
                status.update({
                    "phase": phase,
                    "blocker": blocker,
                    "last_scan_at": now(),
                    "last_commit": snap["commit"],
                    "r2_receipt_present": snap["r2_receipt_present"],
                    "r2_reviews": snap["r2_reviews"],
                    "manifest_present": snap["manifest_present"],
                    "r2_task_row": snap["r2_task_row"],
                    "consecutive_failures": 0,
                    "next_backoff_seconds": args.interval,
                    "running": True,
                })
                write_status(status)
                append_ledger({"ts": now(), "event": "scan_ok", "commit": snap["commit"][:12],
                               "phase": phase, "blocker": blocker,
                               "r2_receipt": snap["r2_receipt_present"],
                               "r2_reviews": snap["r2_reviews"],
                               "manifest": snap["manifest_present"]})
                print("[%s] phase=%s blocker=%s commit=%s r2_receipt=%s"
                      % (now(), phase, blocker, snap["commit"][:12], snap["r2_receipt_present"]))
                backoff = args.interval
            except Exception as exc:  # noqa: BLE001
                failures = status.get("consecutive_failures", 0) + 1
                backoff = min(MAX_BACKOFF, max(args.interval, args.interval * (2 ** failures)))
                status.update({"consecutive_failures": failures,
                               "next_backoff_seconds": backoff,
                               "last_error": str(exc)[:400],
                               "last_scan_at": now(),
                               "running": True})
                write_status(status)
                append_ledger({"ts": now(), "event": "scan_failed", "failures": failures,
                               "backoff": backoff, "error": str(exc)[:400]})
                print("[%s] 扫描失败（第 %d 次），退避 %.0fs：%s"
                      % (now(), failures, backoff, str(exc)[:160]))

            if args.once or (args.cycles and cycles >= args.cycles):
                break
            time.sleep(backoff)
    finally:
        status["running"] = False
        status["stopped_at"] = now()
        write_status(status)
        append_ledger({"ts": now(), "event": "waiter_stop", "cycles": cycles})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
