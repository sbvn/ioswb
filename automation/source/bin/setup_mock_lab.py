#!/usr/bin/env python3
"""搭一个自包含的 mock 实验场（用于常驻监听演示与手工联调）。

产物全部在 automation/mocklab/ 下：
  mocklab/remote/            本机 git 仓库，充当“协作仓库”
  mocklab/config/            该实验场的配置与信任钉
  mocklab/state/ outbox/     运行目录

不访问网络、不碰手机、不影响 automation/state 下的真实运行状态。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOCKLAB = ROOT / "mocklab"
BRANCH = "cursor/init-collab-docs-2e45"

TASK_BODY = """# MOCK-900 常驻监听演示任务

本任务由 `setup_mock_lab.py` 生成，只验证自动执行器的领取-执行-回执-上传链路，
不涉及手机、设备、注册或凭据。

## 要求

1. 产出一份脱敏回执，写到 RECEIPT.md。
2. 回执里不要出现设备标识、手机号、个人路径或凭据。
"""

RECEIPT_HINT = """# MOCK-900 回执

- 结论：mock 常驻监听链路贯通
- 执行方：本地 mock harness
- 是否接触手机：否
"""

_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "01 mock",
    "GIT_COMMITTER_NAME": "01 mock",
    "GIT_AUTHOR_EMAIL": "01-mock@example.invalid",
    "GIT_COMMITTER_EMAIL": "01-mock@example.invalid",
}


def git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(_GIT_ENV)
    proc = subprocess.run(["git"] + args, cwd=str(cwd), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise SystemExit("git %s 失败: %s" % (" ".join(args), (proc.stderr or proc.stdout)[:500]))
    return proc


def force_rmtree(path: Path) -> None:
    def onerror(func, target, _exc):  # noqa: ANN001
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:  # noqa: BLE001
            pass

    shutil.rmtree(path, onerror=onerror)


def main() -> int:
    if MOCKLAB.exists():
        force_rmtree(MOCKLAB)
    remote = MOCKLAB / "remote"
    (remote / "tasks").mkdir(parents=True)
    (MOCKLAB / "config" / "trust").mkdir(parents=True)

    git(["init", "-q", "-b", BRANCH, "."], remote)
    (remote / "README.md").write_bytes(b"# mock lab remote\n")
    task_bytes = TASK_BODY.encode("utf-8")
    (remote / "tasks" / "MOCK-900.md").write_bytes(task_bytes)
    git(["add", "-A"], remote)
    git(["commit", "-q", "-m", "seed mock task"], remote)
    task_commit = git(["rev-parse", "HEAD"], remote).stdout.strip()

    manifest = {
        "schema": "ioswb-release-manifest/1",
        "protocol_version": 1,
        "generated_at": "2026-11-17T00:00:00+08:00",
        "tasks": [
            {
                "task_id": "MOCK-900",
                "revision": 1,
                "status": "published",
                "task_path": "tasks/MOCK-900.md",
                "task_commit": task_commit,
                "content_sha256": hashlib.sha256(task_bytes).hexdigest(),
                "scopes": ["offline-testing"],
                "title": "常驻监听演示任务",
                "meta": {"mock_harness": {"sleep_ms": 400, "receipt": RECEIPT_HINT}},
            }
        ],
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    (remote / "manifest").mkdir()
    (remote / "manifest" / "releases.json").write_bytes(manifest_bytes)
    git(["add", "-A"], remote)
    git(["commit", "-q", "-m", "seed manifest"], remote)
    head = git(["rev-parse", "HEAD"], remote).stdout.strip()
    # 让 HEAD 脱离分支，允许执行器推送回执；分支指向最新提交
    git(["checkout", "-q", "--detach"], remote)
    git(["branch", "-f", BRANCH, head], remote)

    trust = {
        "schema": "ioswb-trust/1",
        "allow": {
            "pinned_manifest_sha256": [hashlib.sha256(manifest_bytes).hexdigest()],
            "pinned_commit": [],
            "signed_commit_fingerprints": [],
        },
    }
    (MOCKLAB / "config" / "trust" / "publishers.json").write_text(
        json.dumps(trust, ensure_ascii=False, indent=2), encoding="utf-8")

    config = {
        "schema": "ioswb-automation-config/1",
        "mode": "mock",
        "poll": {"interval_seconds": 60},
        "repo": {
            "url": str(remote).replace("\\", "/"),
            "branch": BRANCH,
            "manifest_path": "manifest/releases.json",
            "pause_flag_path": "manifest/PAUSE",
            "results_root": "results",
            "allow_main_fallback": False,
        },
        "scope": {"allowed": ["framework-development", "offline-testing"]},
        "limits": {
            "max_attempts_per_revision": 1,
            "upload_retries": 2,
            "task_timeout_seconds": 120,
            "cancel_grace_seconds": 5,
            "scan_inflight_seconds": 2,
        },
        "trust_file": "trust/publishers.json",
        "harness": {
            "unattended": {
                "kind": "dsh-headless",
                "enabled": False,
                "product_version_allow": ["0.2.2-rc.3"],
                "permission_mode": "workspace-write",
                "approval_policy": "never",
            },
            "mock": {"enabled": True, "command": []},
        },
        "live": {"enabled": False, "reason": "mock 实验场，永不启用 live"},
    }
    cfg_path = MOCKLAB / "config" / "automation.mock.json"
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "mocklab": str(MOCKLAB),
        "config": str(cfg_path),
        "branch": BRANCH,
        "task": "MOCK-900@r1",
        "start": "py -3.12 automation/bin/dsh_worker.py --config automation/mocklab/config/automation.mock.json",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
