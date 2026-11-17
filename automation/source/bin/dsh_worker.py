#!/usr/bin/env python3
"""worker 入口。

用法：
  py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json
  py -3.12 automation/bin/dsh_worker.py --config ... --once
  py -3.12 automation/bin/dsh_worker.py --config ... --verify-entry

退出码：0 正常/无事可做；2 配置或协议错误；3 锁被占用；4 已停止；5 需要人工恢复；6 运行错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from executor.common import ConfigError  # noqa: E402
from executor.config import load_config  # noqa: E402
from executor.runner import probe_product  # noqa: E402
from executor.worker import Worker  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IOSWB 自动任务执行器 worker")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--mode", choices=["dry-run", "mock", "live"], default=None,
                        help="覆盖配置里的 mode（默认用配置值）")
    parser.add_argument("--once", action="store_true", help="只跑一个周期就退出")
    parser.add_argument("--max-cycles", type=int, default=0, help="最多跑 N 个周期后退出")
    parser.add_argument("--verify-entry", action="store_true",
                        help="只做只读核验：本机 Harness 版本与无人值守入口，然后退出")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print("[配置] 拒绝启动：%s" % exc)
        return 2

    if args.verify_entry:
        product = probe_product(cfg)
        print(json.dumps({
            "product": product.get("version"),
            "help_ok": product.get("help_ok"),
            "version_allowed": product.get("version_allowed"),
            "ok": product.get("ok"),
            "errors": product.get("errors", []),
            "documented_entry": "dsh --profile headless \"<task>\"",
            "doc_refs": ["@deepseek-ai/dsh-headless/README.md"],
        }, ensure_ascii=False, indent=2))
        return 0 if product.get("ok") else 5

    worker = Worker(cfg, mode=args.mode, once=args.once, max_cycles=args.max_cycles)
    return worker.run()


if __name__ == "__main__":
    raise SystemExit(main())
