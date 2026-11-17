#!/usr/bin/env python3
"""一次连接的独立等待器 / 派发器（标准库，不调用模型）。

依据：`automation/CONNECT_ONCE.md`、`tasks/AUTO-CONNECT-001.md`、`tasks/AUTO-CONNECT-001-r2.md`。

职责（r2 桥接后）：
- 每 60 秒只读扫描唯一 ref 的 TASKS.md、reviews/、manifest/releases.json；
- **每轮先读本机 STOP**，STOP 跨重启有效；命中即写「已停止，不是常驻」并退出（退出码 4）；
- STOP 时不得扫描、不得派发，也不得声称仍在常驻；
- `--dispatch` 且 mode 不是 dry-run 时，交给 executor.worker 执行一次（签名门禁、清单门禁、
  scope、claim、STOP 全部由 worker 判定）；dry-run 只记录「会做什么」，不执行；
- 台账在 `automation/state/connect/`，跨重启保留；扫描失败退避 60/120/240…（上限 15 分钟）。

不读取 token、不打印凭据、不新增系统服务、不调用模型。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # automation/
sys.path.insert(0, str(ROOT))

from executor.common import ConfigError  # noqa: E402
from executor.config import load_config  # noqa: E402
from executor.worker import Worker  # noqa: E402

STATE = ROOT / "state" / "connect"
STATUS = STATE / "status.json"
LEDGER = STATE / "scan.jsonl"
HANDOFF = ROOT / "state" / "handoff" / "AUTO-CONNECT-001.json"
MAX_BACKOFF = 900.0
WATCH = ("TASKS.md", "reviews/", "manifest/releases.json")


def configure_state(path: Path) -> None:
    """测试可以指定独立台账目录，避免动到生产等待器状态。"""
    global STATE, STATUS, LEDGER, HANDOFF
    STATE = path
    STATUS = path / "status.json"
    LEDGER = path / "scan.jsonl"
    HANDOFF = path / "AUTO-CONNECT-001-handoff.json"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def ensure_state() -> None:
    STATE.mkdir(parents=True, exist_ok=True)


def read_status() -> dict:
    if STATUS.exists():
        try:
            return json.loads(STATUS.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
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


def write_handoff(payload: dict) -> None:
    HANDOFF.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "ioswb-handoff/1",
        "task_id": "AUTO-CONNECT-001",
        "revision": 2,
        "attempt": 1,
        "phase": payload.get("phase", "3"),
        "blocker": payload.get("blocker"),
        "digest": payload.get("last_commit"),
        "summary": "phase=%s blocker=%s commit=%s" % (
            payload.get("phase"), payload.get("blocker"),
            (payload.get("last_commit") or "")[:12]),
        "updated_at": now(),
        "artifacts": {"receipt_dir": "results/AUTO-CONNECT-001/r2/",
                      "status": "automation/state/connect/status.json"},
    }
    tmp = HANDOFF.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(HANDOFF)


def git(args: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return subprocess.run(["git"] + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env)


def refresh_ref(cfg, clone_dir: Path) -> Path:
    if not (clone_dir / ".git").exists():
        git(["clone", "--quiet", "--depth", "1", "--branch", cfg.repo_branch, cfg.repo_url,
             str(clone_dir)], timeout=300)
    else:
        git(["-C", str(clone_dir), "fetch", "--quiet", "--depth", "1", "origin",
             cfg.repo_branch], timeout=300)
        git(["-C", str(clone_dir), "reset", "--quiet", "--hard", "FETCH_HEAD"], timeout=120)
    return clone_dir


def scan(cfg) -> dict:
    head = git(["ls-remote", "--heads", cfg.repo_url, cfg.repo_branch], timeout=60)
    if head.returncode != 0:
        raise RuntimeError(((head.stderr or head.stdout) or "").strip()[:300])
    remote_commit = (head.stdout.split() or [""])[0]
    if not remote_commit:
        raise RuntimeError("远端没有该 ref")

    clone_dir = refresh_ref(cfg, STATE / "ref")
    commit = git(["-C", str(clone_dir), "rev-parse", "HEAD"], timeout=60).stdout.strip()
    files = sorted(str(p.relative_to(clone_dir)).replace("\\", "/")
                   for p in clone_dir.rglob("*") if p.is_file() and ".git" not in p.parts)
    tasks_path = clone_dir / "TASKS.md"
    tasks_md = tasks_path.read_text(encoding="utf-8", errors="replace") if tasks_path.exists() else ""
    reviews = [f for f in files if f.startswith("reviews/") and f.endswith(".md")]
    manifest_present = cfg.manifest_path in files
    manifest_tasks: list[str] = []
    if manifest_present:
        try:
            payload = json.loads((clone_dir / cfg.manifest_path).read_text(encoding="utf-8"))
            manifest_tasks = ["%s@r%s" % (t.get("task_id"), t.get("revision"))
                              for t in payload.get("tasks", []) if isinstance(t, dict)]
        except Exception:  # noqa: BLE001
            manifest_tasks = ["<清单无法解析>"]
    bridge_reviews = [r for r in reviews if "AUTO-CONNECT-001-r2" in r]
    smoke_reviews = [r for r in reviews if "SMOKE" in r.upper()]
    return {
        "commit": commit or remote_commit,
        "manifest_present": manifest_present,
        "manifest_tasks": manifest_tasks,
        "reviews": reviews,
        "bridge_reviews": bridge_reviews,
        "smoke_reviews": smoke_reviews,
        "r2_receipt_present": "results/IOS-002/r2/a1.md" in files,
        "tasks_row": [line.strip() for line in tasks_md.splitlines()
                      if line.strip().startswith("| AUTO-CONNECT-001") and "r2" in line][:1],
    }


def decide(snap: dict, stopped: bool) -> tuple[str, str]:
    if stopped:
        return "stopped", "本机 STOP"
    if snap["smoke_reviews"]:
        return "5", "01 已出 smoke 相关验收"
    if snap["bridge_reviews"]:
        return "4", "桥接已实现，等待用户外带确认或 01 的 smoke 授权"
    return "3", "桥接实现中（尚未提交）"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AUTO-CONNECT-001 等待器 / 派发器")
    parser.add_argument("--config", default=str(ROOT / "config" / "automation.json"))
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--cycles", type=int, default=0, help="0 表示不限")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dispatch", action="store_true",
                        help="mode 不是 dry-run 时，每轮最多派发一个任务给 executor.worker")
    parser.add_argument("--state-dir", default=None,
                        help="台账目录（默认 automation/state/connect；测试用独立目录）")
    args = parser.parse_args(argv)

    if args.state_dir:
        configure_state(Path(args.state_dir))
    cfg = load_config(args.config)
    ensure_state()
    previous = read_status()
    restart_note = "上次已退出（进程不在），之前不是常驻" if previous.get("running") else ""
    status = {
        "schema": "ioswb-connect-status/1",
        "pid": os.getpid(),
        "started_at": previous.get("started_at") or now(),
        "running": True,
        "restart_note": restart_note,
        "ref": cfg.repo_branch,
        "mode": cfg.mode,
        "dispatch": bool(args.dispatch),
        "phase": previous.get("phase", "3"),
        "blocker": previous.get("blocker", "桥接实现中"),
        "last_scan_at": previous.get("last_scan_at"),
        "last_commit": previous.get("last_commit"),
        "stop_file": str(cfg.stop_path),
        "stop_seen": False,
        "consecutive_failures": int(previous.get("consecutive_failures") or 0),
    }
    write_status(status)
    append_ledger({"ts": now(), "event": "waiter_start", "mode": cfg.mode,
                   "dispatch": bool(args.dispatch), "restart_note": restart_note})
    write_handoff(status)

    stopped = cfg.stop_path.exists()
    if stopped:
        status.update({"running": False, "phase": "stopped", "blocker": "本机 STOP",
                       "stop_seen": True, "stopped_at": now()})
        write_status(status)
        write_handoff(status)
        append_ledger({"ts": now(), "event": "stop_seen", "phase": "stopped"})
        print("[%s] 本机 STOP 存在：不扫描、不派发。已停止，不是常驻。" % now())
        return 4

    cycles = 0
    backoff = args.interval
    exit_code = 0
    try:
        while True:
            if cfg.stop_path.exists():
                status.update({"running": False, "phase": "stopped", "blocker": "本机 STOP",
                               "stop_seen": True, "stopped_at": now()})
                write_status(status)
                write_handoff(status)
                append_ledger({"ts": now(), "event": "stop_seen", "phase": "stopped"})
                print("[%s] 检测到 STOP：停止扫描与派发。已停止，不是常驻。" % now())
                return 4

            cycles += 1
            try:
                snap = scan(cfg)
                phase, blocker = decide(snap, stopped=False)
                dispatch_result = ""
                if args.dispatch and cfg.mode != "dry-run" and snap["manifest_present"]:
                    if cfg.stop_path.exists():
                        continue
                    code = Worker(cfg, mode=cfg.mode, once=True).run()
                    dispatch_result = "worker_exit=%s" % code
                    append_ledger({"ts": now(), "event": "dispatch", "worker_exit": code})
                    if code == 4:
                        exit_code = 4
                        break
                status.update({
                    "phase": phase, "blocker": blocker, "last_scan_at": now(),
                    "last_commit": snap["commit"], "manifest_present": snap["manifest_present"],
                    "manifest_tasks": snap["manifest_tasks"],
                    "bridge_reviews": snap["bridge_reviews"],
                    "smoke_reviews": snap["smoke_reviews"],
                    "r2_receipt_present": snap["r2_receipt_present"],
                    "tasks_row": snap["tasks_row"],
                    "consecutive_failures": 0,
                    "next_backoff_seconds": args.interval,
                    "running": True,
                    "last_dispatch": dispatch_result,
                })
                write_status(status)
                write_handoff(status)
                append_ledger({"ts": now(), "event": "scan_ok", "commit": snap["commit"][:12],
                               "phase": phase, "blocker": blocker,
                               "manifest": snap["manifest_present"],
                               "tasks": snap["manifest_tasks"],
                               "bridge_reviews": snap["bridge_reviews"]})
                print("[%s] phase=%s blocker=%s commit=%s manifest=%s %s"
                      % (now(), phase, blocker, snap["commit"][:12],
                         snap["manifest_present"], snap["manifest_tasks"]))
                backoff = args.interval
            except ConfigError as exc:
                print("[配置] %s" % exc)
                return 2
            except Exception as exc:  # noqa: BLE001
                failures = int(status.get("consecutive_failures") or 0) + 1
                backoff = min(MAX_BACKOFF, max(args.interval, args.interval * (2 ** failures)))
                status.update({"consecutive_failures": failures,
                               "next_backoff_seconds": backoff,
                               "last_error": str(exc)[:400],
                               "last_scan_at": now(), "running": True})
                write_status(status)
                append_ledger({"ts": now(), "event": "scan_failed", "failures": failures,
                               "backoff": backoff, "error": str(exc)[:400]})
                print("[%s] 扫描失败（第 %d 次），退避 %.0fs：%s"
                      % (now(), failures, backoff, str(exc)[:160]))

            if args.once or (args.cycles and cycles >= args.cycles):
                break

            deadline = time.time() + backoff
            while time.time() < deadline:
                if cfg.stop_path.exists():
                    break
                time.sleep(min(1.0, max(0.05, deadline - time.time())))
    finally:
        stopped_now = cfg.stop_path.exists()
        status["running"] = False
        status["stopped_at"] = now()
        if stopped_now:
            status["phase"] = "stopped"
            status["blocker"] = "本机 STOP"
            status["stop_seen"] = True
        write_status(status)
        append_ledger({"ts": now(), "event": "waiter_stop", "cycles": cycles,
                       "stopped": stopped_now})
    if exit_code == 4 or cfg.stop_path.exists():
        print("已停止，不是常驻。")
        return 4
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
