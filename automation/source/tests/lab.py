"""离线测试实验台：在本机构造一个“协作仓库”和一套隔离运行目录。

不连接手机、不访问网络：远端就是本机临时目录里的 git 仓库。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
AUTOMATION_ROOT = TESTS_DIR.parent
WORK_ROOT = TESTS_DIR / ".work"
WORKER_BIN = AUTOMATION_ROOT / "bin" / "dsh_worker.py"
CONTROL_BIN = AUTOMATION_ROOT / "bin" / "dsh_control.py"
BRANCH = "cursor/init-collab-docs-2e45"

_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "01 mock",
    "GIT_COMMITTER_NAME": "01 mock",
    "GIT_AUTHOR_EMAIL": "01-mock@example.invalid",
    "GIT_COMMITTER_EMAIL": "01-mock@example.invalid",
}


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(_GIT_ENV)
    proc = subprocess.run(["git"] + args, cwd=str(cwd), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError("git %s 失败: %s" % (" ".join(args), (proc.stderr or proc.stdout)[:600]))
    return proc


def _force_rmtree(path: Path) -> None:
    """Windows 上 .git 对象是只读的，rmtree 需要先改权限。"""
    import stat as _stat

    def onerror(func, target, _exc):  # noqa: ANN001
        try:
            os.chmod(target, _stat.S_IWRITE)
            func(target)
        except Exception:  # noqa: BLE001
            pass

    shutil.rmtree(path, onerror=onerror)


class Lab:
    def __init__(self, name: str, *, checked_out_remote: bool = False,
                 sign_key: Path | None = None) -> None:
        self.name = name
        self.root = WORK_ROOT / name
        if self.root.exists():
            _force_rmtree(self.root)
        (self.root / "config" / "trust").mkdir(parents=True, exist_ok=True)
        self.remote = self.root / "remote"
        self.exec_log = self.root / "exec.log"
        self.config_path = self.root / "config" / "automation.json"
        self.trust_path = self.root / "config" / "trust" / "publishers.json"
        self.sign_key = sign_key
        self._tasks: list[dict] = []
        self.checked_out_remote = checked_out_remote
        self.manifest_commit: str | None = None
        self._init_remote()

    # ---------------------------------------------------------- 远端

    def commit_all(self, message: str) -> None:
        args = ["commit", "-q", "-m", message]
        if self.sign_key:
            # git 的 -c 必须位于子命令之前
            args = (["-c", "gpg.format=ssh",
                     "-c", "user.signingkey=%s" % self.sign_key] + args + ["-S"])
        _git(args, self.remote)

    def _init_remote(self) -> None:
        self.remote.mkdir(parents=True, exist_ok=True)
        _git(["init", "-q", "-b", BRANCH, "."], self.remote)
        (self.remote / "README.md").write_bytes(b"# mock collab repo\n")
        _git(["add", "-A"], self.remote)
        self.commit_all("init")

    def plan_task(self, task_id: str, *, revision: int = 1, scopes=("offline-testing",),
                  body: str | None = None, status: str = "published",
                  mock: dict | None = None, commit: bool = True,
                  content_override: str | None = None) -> dict:
        task_path = "tasks/%s.md" % task_id
        text = body if body is not None else (
            "# %s 离线测试任务\n\n本任务仅用于自动化框架的离线验证，不涉及手机操作。\n" % task_id
        )
        data = text.encode("utf-8")
        target = self.remote / task_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        commit_sha = ""
        if commit:
            _git(["add", "-A"], self.remote)
            self.commit_all("task %s" % task_id)
            commit_sha = _git(["rev-parse", "HEAD"], self.remote).stdout.strip()
        import hashlib

        digest = (content_override or hashlib.sha256(data).hexdigest())
        entry = {
            "task_id": task_id,
            "revision": revision,
            "status": status,
            "task_path": task_path,
            "task_commit": commit_sha,
            "content_sha256": digest,
            "scopes": list(scopes),
            "title": "%s mock task" % task_id,
        }
        if mock:
            entry["meta"] = {"mock_harness": mock}
        self._tasks = [t for t in self._tasks if not (t["task_id"] == task_id and t["revision"] == revision)]
        self._tasks.append(entry)
        self._review_commit = None
        return entry

    def publish(self, *, tasks: list[dict] | None = None) -> str:
        payload = {
            "schema": "ioswb-release-manifest/1",
            "protocol_version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "tasks": tasks if tasks is not None else self._tasks,
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        target = self.remote / "manifest" / "releases.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        _git(["add", "-A"], self.remote)
        self.commit_all("manifest")
        sha = _git(["rev-parse", "HEAD"], self.remote).stdout.strip()
        self.manifest_commit = sha
        if not self.checked_out_remote:
            # HEAD 脱离分支，允许被 push（否则非裸仓库会以 denyCurrentBranch 拒绝推送）
            _git(["checkout", "-q", "--detach"], self.remote)
            _git(["branch", "-f", BRANCH, sha], self.remote)
        return sha

    def manifest_bytes(self) -> bytes:
        return (self.remote / "manifest" / "releases.json").read_bytes()

    def manifest_sha(self) -> str:
        import hashlib

        return hashlib.sha256(self.manifest_bytes()).hexdigest()

    def set_pause_flag(self, present: bool = True) -> None:
        path = self.remote / "manifest" / "PAUSE"
        if present:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"paused\n")
        elif path.exists():
            path.unlink()
        _git(["add", "-A"], self.remote)
        self.commit_all("pause %s" % present)
        head = _git(["rev-parse", "HEAD"], self.remote).stdout.strip()
        if not self.checked_out_remote:
            _git(["checkout", "-q", "--detach"], self.remote)
            _git(["branch", "-f", BRANCH, head], self.remote)

    def allow_push(self) -> None:
        """解除 denyCurrentBranch：把 HEAD 从分支移开。"""
        _git(["checkout", "-q", "--detach"], self.remote)

    def commit_remote_file(self, rel_path: str, text: str) -> str:
        """在远端分支上直接提交一个文件（用于伪造回执）。"""
        target = self.remote / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        _git(["add", "-A"], self.remote)
        self.commit_all("forge %s" % rel_path)
        head = _git(["rev-parse", "HEAD"], self.remote).stdout.strip()
        if not self.checked_out_remote:
            _git(["checkout", "-q", "--detach"], self.remote)
            _git(["branch", "-f", BRANCH, head], self.remote)
        return head

    # ---------------------------------------------------------- 信任 / 配置

    def write_trust(self, pins: list[str] | None = None, commits: list[str] | None = None,
                    fingerprints: list[str] | None = None,
                    signers: list[dict] | None = None) -> None:
        payload = {
            "schema": "ioswb-trust/1",
            "allow": {
                "pinned_manifest_sha256": pins or [],
                "pinned_commit": commits or [],
                "signed_commit_fingerprints": fingerprints or [],
            },
        }
        if signers is not None:
            payload["signers"] = signers
        self.trust_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def pin_manifest(self, *, bound: bool = True) -> None:
        """默认写「摘要:提交」形式的绑定钉（协议要求摘要钉必须绑定 commit）。"""
        digest = self.manifest_sha()
        commit = getattr(self, "manifest_commit", None)
        if bound and commit:
            self.write_trust(pins=["%s:%s" % (digest, commit)])
        else:
            self.write_trust(pins=[digest])

    def write_config(self, mode: str = "mock", *, trust: bool = True, **overrides) -> Path:
        payload = {
            "schema": "ioswb-automation-config/1",
            "mode": mode,
            "poll": {"interval_seconds": 5},
            "repo": {
                "url": str(self.remote).replace("\\", "/"),
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
                "task_timeout_seconds": 60,
                "cancel_grace_seconds": 5,
                "scan_inflight_seconds": 1,
            },
            "trust_file": "trust/publishers.json",
            "harness": {
                "unattended": {
                    "kind": "dsh-headless",
                    "enabled": mode == "live",
                    "product_version_allow": ["0.2.2-rc.3"],
                    "permission_mode": "workspace-write",
                    "approval_policy": "never",
                    "timeout_seconds": 60,
                    "documented": ["@deepseek-ai/dsh-headless/README.md"],
                },
                "mock": {"enabled": True, "command": []},
            },
            "live": {"enabled": mode == "live",
                     "reason": "" if mode == "live" else "测试环境不启用 live"},
        }
        payload.update(overrides)
        if trust is False:
            self.trust_path.unlink(missing_ok=True)
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.config_path

    # ---------------------------------------------------------- 运行

    def _env(self, extra_env: dict | None = None) -> dict:
        env = dict(os.environ)
        env["MOCK_EXEC_LOG"] = str(self.exec_log)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHON"] = sys.executable
        env.pop("IOSWB_FAULT_INJECT_PHASE", None)
        # 干净 HOME 下也要能提交：worker 的 git 提交需要身份（审核复跑发现的问题）
        env.setdefault("GIT_AUTHOR_NAME", "ioswb-automation")
        env.setdefault("GIT_COMMITTER_NAME", "ioswb-automation")
        env.setdefault("GIT_AUTHOR_EMAIL", "automation@example.invalid")
        env.setdefault("GIT_COMMITTER_EMAIL", "automation@example.invalid")
        if extra_env:
            env.update(extra_env)
        return env

    def run_worker(self, *extra: str, timeout: float = 180.0,
                   extra_env: dict | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(WORKER_BIN), "--config", str(self.config_path)] + list(extra)
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=self._env(extra_env), timeout=timeout)

    def run_waiter(self, *extra: str, timeout: float = 180.0,
                   extra_env: dict | None = None) -> subprocess.CompletedProcess:
        waiter = AUTOMATION_ROOT / "bin" / "connect_wait.py"
        state_dir = self.root / "state" / "connect"
        cmd = [sys.executable, str(waiter), "--config", str(self.config_path),
               "--state-dir", str(state_dir), "--once"] + list(extra)
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=self._env(extra_env), timeout=timeout)

    def waiter_ledger(self) -> list[dict]:
        path = self.root / "state" / "connect" / "scan.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def start_worker(self, *extra: str, extra_env: dict | None = None) -> subprocess.Popen:
        cmd = [sys.executable, str(WORKER_BIN), "--config", str(self.config_path)] + list(extra)
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                env=self._env(extra_env))

    def harness_spec(self, key: str = "MOCK-001@r1", attempt: int = 1) -> dict | None:
        # worker 的 attempt 目录名是 "<task_id>_r<rev>-a<n>"
        path = (self.root / "state" / "attempts" /
                ("%s-a%d" % (key.replace("@", "_"), attempt)) / "harness.spec.json")
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def handoff(self, task_id: str = "MOCK-001") -> dict | None:
        path = self.root / "state" / "handoff" / ("%s.json" % task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def protocol_states(self) -> dict:
        import sys as _sys
        _sys.path.insert(0, str(AUTOMATION_ROOT))
        from executor.ledger import Ledger
        ledger = Ledger(self.root / "state" / "ledger.jsonl")
        ledger.load()
        return {k: ledger.protocol_state(k) for k in ledger.attempts()}

    def run_control(self, *args: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(CONTROL_BIN), "--config", str(self.config_path)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=self._env(), timeout=timeout)

    # ---------------------------------------------------------- 观测

    def ledger(self) -> list[dict]:
        path = self.root / "state" / "ledger.jsonl"
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def events(self, name: str) -> list[dict]:
        return [r for r in self.ledger() if r.get("event") == name]

    def exec_starts(self) -> int:
        if not self.exec_log.exists():
            return 0
        return sum(1 for line in self.exec_log.read_text(encoding="utf-8").splitlines()
                   if " start " in line)

    def exec_ends(self) -> int:
        if not self.exec_log.exists():
            return 0
        return sum(1 for line in self.exec_log.read_text(encoding="utf-8").splitlines()
                   if line.endswith(" end"))

    def remote_has(self, rel_path: str) -> bool:
        proc = _git(["cat-file", "-e", "%s:%s" % (BRANCH, rel_path)], self.remote, check=False)
        return proc.returncode == 0

    def remote_read(self, rel_path: str) -> str | None:
        proc = _git(["show", "%s:%s" % (BRANCH, rel_path)], self.remote, check=False)
        return proc.stdout if proc.returncode == 0 else None

    def remote_commit_count(self) -> int:
        return int(_git(["rev-list", "--count", BRANCH], self.remote).stdout.strip())

    def stop(self, note: str = "test") -> None:
        state = self.root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "STOP").write_text(json.dumps({"note": note}), encoding="utf-8")

    def resume(self) -> None:
        (self.root / "state" / "STOP").unlink(missing_ok=True)

    def outbox_files(self) -> list[str]:
        base = self.root / "outbox"
        if not base.exists():
            return []
        return sorted(str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*.md"))
