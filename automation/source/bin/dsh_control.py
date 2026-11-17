#!/usr/bin/env python3
"""操作员控制台。

  py -3.12 automation/bin/dsh_control.py --config <cfg> status
  py -3.12 automation/bin/dsh_control.py --config <cfg> stop  [--note "..."]
  py -3.12 automation/bin/dsh_control.py --config <cfg> resume --confirm
  py -3.12 automation/bin/dsh_control.py --config <cfg> ack "IOS-002@r1" [--decision abandoned] [--note "..."]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from executor import control  # noqa: E402
from executor.config import load_config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IOSWB 自动任务执行器控制台")
    parser.add_argument("--config", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")

    p_stop = sub.add_parser("stop")
    p_stop.add_argument("--note", default="")

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("--confirm", action="store_true")
    p_resume.add_argument("--note", default="")

    p_ack = sub.add_parser("ack")
    p_ack.add_argument("attempt", help="形如 IOS-002@r1")
    p_ack.add_argument("--decision", default="abandoned")
    p_ack.add_argument("--note", default="")

    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.command == "status":
        payload = control.status(cfg)
    elif args.command == "stop":
        payload = control.stop(cfg, note=args.note)
    elif args.command == "resume":
        payload = control.resume(cfg, confirm=args.confirm, note=args.note)
    else:
        payload = control.ack(cfg, args.attempt, args.decision, args.note)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
