#!/usr/bin/env python3
"""一条命令复现连续两任务的离线调度。

使用临时目录、合成 SSH 密钥和本地 file remote。不访问网络，不读真实凭据。
这是实现方自测，不是独立验收。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
AUTOMATION_ROOT = TESTS_DIR.parent
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from lab import BRANCH, Lab, _git  # noqa: E402

LOOP = AUTOMATION_ROOT / "bin" / "dsh_loop.py"
DEADLINE = "2027-01-01T00:00:00+08:00"


def _signing_key(lab: Lab):
    key = lab.root / "synthetic-ed25519"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "synthetic-loop@example.invalid",
                    "-f", str(key)], check=True, capture_output=True)
    public_key = (lab.root / "synthetic-ed25519.pub").read_text(encoding="utf-8").strip()
    listing = subprocess.run(["ssh-keygen", "-lf", str(key) + ".pub"], capture_output=True,
                             text=True, encoding="utf-8").stdout
    fingerprint = "SHA256:" + listing.split("SHA256:")[1].split()[0]
    return key, public_key, fingerprint


def _permits(lab: Lab, grants: list[dict]) -> None:
    payload = {"schema": "ioswb-local-permit/1", "saved_login": False, "grants": grants}
    path = lab.root / "config" / "permits.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _grant(task_id: str, revision: int = 1, scopes=("offline-testing",), budget: int = 1,
           deadline: str = DEADLINE) -> dict:
    return {"task_id": task_id, "revision": revision, "scopes": list(scopes),
            "budget": budget, "deadline": deadline}


def _seed_consumed_smoke(lab: Lab) -> None:
    """模拟已经消费的 r1/r2。只写测试台账，不改仓库里的真实回执。"""
    path = lab.root / "state" / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"schema": "ioswb-automation-ledger/1", "seq": 1, "event": "claim",
         "attempt": "SMOKE-001@r1", "task_id": "SMOKE-001", "revision": 1},
        {"schema": "ioswb-automation-ledger/1", "seq": 2, "event": "attempt_failed",
         "attempt": "SMOKE-001@r1", "task_id": "SMOKE-001", "revision": 1},
        {"schema": "ioswb-automation-ledger/1", "seq": 3, "event": "claim",
         "attempt": "SMOKE-001@r2", "task_id": "SMOKE-001", "revision": 2},
        {"schema": "ioswb-automation-ledger/1", "seq": 4, "event": "attempt_upload_ok",
         "attempt": "SMOKE-001@r2", "task_id": "SMOKE-001", "revision": 2},
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


def run_demo(work: Path | None = None) -> dict:
    started = time.time()
    lab = Lab("continuous-demo") if work is None else Lab("continuous-demo")
    key, public_key, fingerprint = _signing_key(lab)
    lab.sign_key = key
    lab.write_trust(signers=[{
        "identity": "synthetic-loop@example.invalid",
        "public_key": public_key,
        "fingerprint": fingerprint,
    }])
    marker = "FLOW-001\nOK\n"
    lab.plan_task("SMOKE-001", revision=1, body="# smoke r1 fixture\n",
                  mock={"sleep_ms": 20, "receipt": "SMOKE-001\n"})
    lab.plan_task("SMOKE-001", revision=2, body="# smoke r2 fixture\n",
                  mock={"sleep_ms": 20, "receipt": "SMOKE-001\n"})
    lab.plan_task("FLOW-001", body="# FLOW-001\n",
                  mock={"sleep_ms": 30, "receipt": marker,
                        "command": "injected-command", "args": ["--patch", "/tmp/not-used"]})
    lab.publish()
    lab.write_config(mode="dry-run")
    _permits(lab, [_grant("FLOW-001"), _grant("FLOW-002")])
    _seed_consumed_smoke(lab)
    config_before = lab.config_path.read_bytes()
    env = lab._env()
    env["DSH_NODE_EXECUTABLE"] = ""
    env["DSH_INSTALL_DIR"] = ""
    proc = subprocess.Popen(
        [sys.executable, str(LOOP), "--config", str(lab.config_path),
         "--dispatch", "--offline-run"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    summary = {"returncode": None, "model_requests": 0, "ok": False, "log": ""}
    try:
        deadline = time.time() + 40
        while time.time() < deadline and not lab.remote_has("results/FLOW-001/r1/a1.md"):
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        _git(["merge", "--ff-only", BRANCH], lab.remote)
        lab.plan_task("FLOW-002", body="# FLOW-002\n",
                      mock={"sleep_ms": 30, "receipt": "FLOW-002\nOK\n"})
        lab.publish()
        while time.time() < deadline and not lab.remote_has("results/FLOW-002/r1/a1.md"):
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        lab.stop("demo stop")
        try:
            stdout, _ = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, _ = proc.communicate(timeout=5)
        summary["returncode"] = proc.returncode
        summary["log"] = stdout or ""
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    raw_1 = lab.remote_has("results/FLOW-001/r1/a1.md")
    meta_1 = lab.remote_has("results/FLOW-001/r1/a1.meta.json")
    raw_2 = lab.remote_has("results/FLOW-002/r1/a1.md")
    meta_2 = lab.remote_has("results/FLOW-002/r1/a1.meta.json")
    smoke_new = lab.remote_has("results/SMOKE-001/r1/a1.md") or lab.remote_has(
        "results/SMOKE-001/r2/a1.md")
    patch_left = (lab.root / "state" / "overlay-empty.yml").exists() or (
        lab.root / "state" / "overlay.json").exists()
    config_same = lab.config_path.read_bytes() == config_before
    starts = lab.exec_starts()
    summary.update({
        "exec_starts": starts,
        "raw_1": raw_1,
        "meta_1": meta_1,
        "raw_2": raw_2,
        "meta_2": meta_2,
        "smoke_uploaded": smoke_new,
        "patch_left": patch_left,
        "config_same": config_same,
        "duration_seconds": round(time.time() - started, 3),
        "model_requests": summary["log"].count("model_requests=0") and 0,
    })
    if meta_1:
        text = lab.remote_read("results/FLOW-001/r1/a1.meta.json") or ""
        meta = json.loads(text)
        summary["marker_ok"] = meta.get("marker_ok")
        summary["final_reason_kind"] = meta.get("final_reason_kind")
        summary["exit_code"] = meta.get("exit_code")
        summary["saved_login"] = meta.get("saved_login")
    raw_text = lab.remote_read("results/FLOW-001/r1/a1.md") or ""
    spec_hits = list((lab.root / "state" / "attempts").glob("*/harness.spec.json")) if (
        lab.root / "state" / "attempts").exists() else []
    spec_blob = "\n".join(path.read_text(encoding="utf-8") for path in spec_hits)
    summary["raw_marker"] = "FLOW-001" in raw_text and "OK" in raw_text
    summary["command_injected"] = "injected-command" in spec_blob
    summary["ok"] = bool(
        summary["returncode"] == 4 and starts == 2 and raw_1 and meta_1 and raw_2 and meta_2
        and not smoke_new and not patch_left and config_same
        and summary.get("marker_ok") is True and summary.get("final_reason_kind") == "completed"
        and summary.get("exit_code") == 0 and summary.get("saved_login") is False
        and summary["raw_marker"] and not summary["command_injected"]
        and "model_requests=0" in summary["log"]
    )
    return summary


def main() -> int:
    if not os.environ.get("GIT_AUTHOR_NAME"):
        os.environ.setdefault("GIT_AUTHOR_NAME", "ioswb-automation")
        os.environ.setdefault("GIT_COMMITTER_NAME", "ioswb-automation")
        os.environ.setdefault("GIT_AUTHOR_EMAIL", "automation@example.invalid")
        os.environ.setdefault("GIT_COMMITTER_EMAIL", "automation@example.invalid")
    summary = run_demo()
    print(json.dumps({k: v for k, v in summary.items() if k != "log"}, ensure_ascii=False, indent=2))
    print("--- log ---")
    print(summary["log"][-2000:])
    print("DEMO %s in %ss" % ("PASS" if summary["ok"] else "FAIL", summary["duration_seconds"]))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
