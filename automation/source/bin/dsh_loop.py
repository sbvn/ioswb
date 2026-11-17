#!/usr/bin/env python3
"""持续调度入口。单进程、单 worker，只跑离线 mock。

磁盘配置保持 dry-run。没有 --dispatch 和 --offline-run 时不领取。
本机 permits.json 写明任务、版本、范围、预算和期限；清单不能自己授权。
不调用真实模型，不读取已保存登录，不改 $DSH_HOME，审批保持 never。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from executor.common import ConfigError  # noqa: E402
from executor.config import load_config  # noqa: E402
from executor.overlay import execution_overlay, scrub_overlay  # noqa: E402
from executor.permit import load_permits  # noqa: E402
from executor.worker import Worker  # noqa: E402


def _blocked_reason(cfg) -> str | None:
    if cfg.mode == "live" or cfg.live_enabled or cfg.harness.enabled:
        return "配置仍允许 live 或真实入口，持续入口拒绝启动"
    if cfg.harness.patch_files:
        return "配置含 patch_files。持续入口不使用已保存登录"
    if cfg.harness.approval_policy != "never":
        return "approval_policy 必须保持 never"
    if cfg.mode != "dry-run":
        return "磁盘 mode 必须是 dry-run。执行只放在进程内的临时 overlay"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IOSWB 持续调度（离线 mock）")
    parser.add_argument("--config", required=True)
    parser.add_argument("--dispatch", action="store_true",
                        help="允许进入调度。单独使用时，dry-run 仍不领取")
    parser.add_argument("--offline-run", action="store_true",
                        help="与 --dispatch 同时给出时，在内存 overlay 里用 fake runner 执行")
    parser.add_argument("--max-cycles", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print("[配置] 拒绝启动：%s" % exc)
        print("model_requests=0")
        return 2

    scrub_overlay(cfg)
    print("model_requests=0")
    reason = _blocked_reason(cfg)
    if reason:
        print("[入口] %s" % reason)
        return 2

    if not (args.dispatch and args.offline_run):
        print("[入口] 没有同时给出 --dispatch 和 --offline-run：保持 dry-run，不领取。")
        return Worker(cfg, mode="dry-run", once=True).run()

    permits = load_permits(cfg.root / "config" / "permits.json")
    if permits.blocked:
        print("[许可] %s" % permits.blocked)
        print("[入口] 授权不足，停止派发，不自动延长。")
        return 0

    print("[入口] 临时 overlay：mock，saved_login=false。磁盘配置保持 dry-run。")
    with execution_overlay(cfg):
        code = Worker(cfg, mode="mock", require_permit=True, max_cycles=args.max_cycles).run()
    print("[入口] overlay 已清理。model_requests=0")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
