#!/usr/bin/env python3
"""mock 用“假 Harness”。

它是一个真实的子进程，用来在完全不接触手机的前提下验证：
- 执行只发生一次；
- 长任务可被 STOP 取消；
- 取消后父进程能确认子进程真的退出；
- 回执写文件（而不是靠 stdout），与真实入口一致。

spec 字段：
  sleep_ms       执行耗时
  receipt        回执正文
  stop_at_end    是否在结束前创建 STOP（模拟“回执刚生成，操作员正好按了停止”）
  stop_file      STOP 文件路径
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PARENT_ENV = "MOCK_HARNESS_PARENT_PID"
EXEC_LOG_ENV = "MOCK_EXEC_LOG"


def log_exec(line: str) -> None:
    """独立于台账的执行计数：测试用它证明“真的只跑了一次”。"""
    path = os.environ.get(EXEC_LOG_ENV)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
            handle.flush()
    except OSError:
        pass


def parent_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    sleep_ms = int(spec.get("sleep_ms") or 0)
    receipt = spec.get("receipt") or "# 模拟回执\n\n本文件由 mock harness 生成，不含真实设备信息。\n"
    stop_at_end = bool(spec.get("stop_at_end"))
    stop_file = spec.get("stop_file")

    parent = int(os.environ.get(PARENT_ENV) or 0)
    log_exec("start parent=%s" % parent)
    deadline = time.time() + sleep_ms / 1000.0
    while time.time() < deadline:
        if parent and not parent_alive(parent):
            log_exec("orphan_exit")
            return 3  # 父进程没了：立即退出，避免测试留下孤儿进程
        time.sleep(0.05)

    if stop_at_end and stop_file:
        Path(stop_file).write_text(
            json.dumps({"requested_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": "mock stop_at_end"},
                       ensure_ascii=False),
            encoding="utf-8",
        )

    Path(args.out).write_text(receipt, encoding="utf-8")
    log_exec("end")
    sys.stdout.write("mock harness done\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
