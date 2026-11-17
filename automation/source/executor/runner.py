"""任务执行适配器。

两个适配器走同一条“子进程 + 超时 + 取消 + 等待退出”的路径，
所以 STOP 语义在 mock 与真实入口上是一致的：
- 取消 = 终止子进程并**等到它真的退出**，然后才允许宣告停止成功；
- 超时 = 先 terminate，宽限后 kill，期间持续 wait；
- 只把 stdout/stderr 落到本机文件，不打印、不入库。
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .common import GitError, now_iso, ensure_dir

# 真实入口的文档依据（安装版本 0.2.2-rc.3 内附文档）：
# @deepseek-ai/dsh-headless/README.md —— "dsh --profile headless \"run the tests\""
#                                     —— 监督者示例：dsh headless --permission-mode workspace-write
#                                        --add-dir <git-dir> --json - < task.txt > run.jsonl
# 启动器帮助 —— `dsh headless "run the tests"` 出现在 Examples。
HEADLESS_DOC_REFS = (
    "@deepseek-ai/dsh-headless/README.md#running-a-one-shot-task",
    "@deepseek-ai/dsh-headless/README.md#supervising-implementation-tasks",
    "@deepseek-ai/dsh-headless/README.md#machine-readable-output",
    "@deepseek-ai/dsh/README.md#entry-modes (dsh --profile headless \"job\")",
)


@dataclass
class RunOutcome:
    status: str                       # success | failed | cancelled | timeout | unreachable
    exit_code: int | None = None
    receipt_text: str | None = None
    error: str = ""
    cancel_confirmed: bool = True
    duration_seconds: float = 0.0
    stdout_path: str | None = None
    stderr_path: str | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "error": self.error,
            "cancel_confirmed": self.cancel_confirmed,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "extra": self.extra,
        }


def _terminate_tree(proc: subprocess.Popen, grace: float) -> bool:
    """终止并等待退出；返回是否确认进程已退出。"""
    if proc.poll() is not None:
        return True
    try:
        proc.terminate()
    except OSError:
        pass
    deadline = time.time() + max(1.0, grace)
    while time.time() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    try:
        proc.kill()
    except OSError:
        pass
    try:
        proc.wait(timeout=max(5.0, grace))
    except subprocess.TimeoutExpired:
        return False
    return proc.poll() is not None


class Runner:
    """子进程执行器基类。"""

    name = "base"

    def __init__(self, cfg, attempt_dir: Path) -> None:
        self.cfg = cfg
        self.attempt_dir = attempt_dir

    def build(self, payload: dict, spec: dict) -> tuple[list[str], str, dict]:
        raise NotImplementedError

    def run(
        self,
        payload: dict,
        spec: dict,
        *,
        timeout: float,
        should_cancel: Callable[[], bool],
        heartbeat: Callable[[str], None] | None = None,
        on_child: Callable[[int], None] | None = None,
    ) -> RunOutcome:
        ensure_dir(self.attempt_dir)
        cmd, stdin_text, env = self.build(payload, spec)
        stdout_path = self.attempt_dir / "harness.stdout.log"
        stderr_path = self.attempt_dir / "harness.stderr.log"
        started = time.time()
        with open(stdout_path, "wb") as out_handle, open(stderr_path, "wb") as err_handle:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.attempt_dir),
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=out_handle,
                    stderr=err_handle,
                    text=False,
                )
            except FileNotFoundError as exc:
                return RunOutcome(status="unreachable", error="可执行文件不存在: %s" % exc,
                                  duration_seconds=time.time() - started)
            if on_child:
                on_child(proc.pid)
            try:
                if stdin_text:
                    try:
                        proc.stdin.write(stdin_text.encode("utf-8"))  # type: ignore[union-attr]
                        proc.stdin.close()  # type: ignore[union-attr]
                    except (BrokenPipeError, OSError):
                        pass
                else:
                    try:
                        proc.stdin.close()  # type: ignore[union-attr]
                    except (BrokenPipeError, OSError):
                        pass

                deadline = started + max(1.0, timeout)
                while True:
                    if proc.poll() is not None:
                        break
                    if should_cancel():
                        confirmed = _terminate_tree(proc, self.cfg.limits.cancel_grace_seconds)
                        return RunOutcome(
                            status="cancelled",
                            exit_code=proc.poll(),
                            error="收到停止信号，已终止子进程",
                            cancel_confirmed=confirmed,
                            duration_seconds=time.time() - started,
                            stdout_path=str(stdout_path),
                            stderr_path=str(stderr_path),
                        )
                    if time.time() > deadline:
                        confirmed = _terminate_tree(proc, self.cfg.limits.cancel_grace_seconds)
                        return RunOutcome(
                            status="timeout",
                            exit_code=proc.poll(),
                            error="执行超时 %ss" % int(timeout),
                            cancel_confirmed=confirmed,
                            duration_seconds=time.time() - started,
                            stdout_path=str(stdout_path),
                            stderr_path=str(stderr_path),
                        )
                    if heartbeat:
                        heartbeat("executing")
                    time.sleep(0.2)
            finally:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _terminate_tree(proc, self.cfg.limits.cancel_grace_seconds)

        exit_code = proc.returncode
        stderr_tail = ""
        try:
            stderr_tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-1200:]
        except OSError:
            pass
        receipt_text = self.collect_receipt()
        duration = time.time() - started
        if exit_code != 0:
            return RunOutcome(status="failed", exit_code=exit_code, error=stderr_tail.strip()[:800],
                              duration_seconds=duration, stdout_path=str(stdout_path),
                              stderr_path=str(stderr_path))
        gate = self.success_gate(exit_code, receipt_text)
        if gate:
            return RunOutcome(status="failed", exit_code=exit_code, error=gate,
                              duration_seconds=duration, stdout_path=str(stdout_path),
                              stderr_path=str(stderr_path))
        if receipt_text is None:
            return RunOutcome(status="failed", exit_code=exit_code,
                              error="执行成功退出但没有产出回执", duration_seconds=duration,
                              stdout_path=str(stdout_path), stderr_path=str(stderr_path))
        return RunOutcome(status="success", exit_code=exit_code, receipt_text=receipt_text,
                          duration_seconds=duration, stdout_path=str(stdout_path),
                          stderr_path=str(stderr_path))

    def success_gate(self, exit_code: int | None, receipt_text: str | None) -> str | None:
        """子类可追加完成条件。默认不再额外收紧。"""
        return None

    def collect_receipt(self) -> str | None:
        receipt = self.attempt_dir / "RECEIPT.md"
        if not receipt.exists():
            return None
        text = receipt.read_text(encoding="utf-8", errors="replace").strip()
        return text or None


class MockRunner(Runner):
    """离线 mock：真实子进程，产出脚本化回执；永不接触设备。"""

    name = "mock"

    def build(self, payload: dict, spec: dict) -> tuple[list[str], str, dict]:
        mock_spec = dict(payload)
        mock_spec.update(spec or {})
        # 任务正文和清单 meta 不能把 command/args 送进子进程。
        mock_spec.pop("command", None)
        mock_spec.pop("args", None)
        spec_path = self.attempt_dir / "harness.spec.json"
        spec_path.write_text(json.dumps(mock_spec, ensure_ascii=False, indent=2), encoding="utf-8")
        harness = Path(__file__).resolve().parent.parent / "tests" / "fake_harness.py"
        cmd = [os.environ.get("PYTHON", "python"), str(harness), "--spec", str(spec_path),
               "--out", str(self.attempt_dir / "RECEIPT.md")]
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["MOCK_HARNESS_PARENT_PID"] = str(os.getpid())
        return cmd, "", env

    def success_gate(self, exit_code: int | None, receipt_text: str | None) -> str | None:
        """fake runner 与真实入口同一条完成规则：exit 0 且 final.reason.kind 为 completed。"""
        if exit_code != 0:
            return None
        path = self.attempt_dir / "final.json"
        if not path.exists():
            return "没有 final 事件"
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "final 事件格式坏"
        reason = event.get("reason") if isinstance(event, dict) else None
        kind = reason.get("kind") if isinstance(reason, dict) else None
        if kind != "completed":
            shown = kind if isinstance(kind, str) else "缺失"
            return "final.reason.kind 为 %s，不是 completed" % shown
        if not (receipt_text and receipt_text.strip()):
            return "exit 0 且 completed，但没有有效任务输出"
        return None


class HeadlessRunner(Runner):
    """真实入口：dsh --profile headless（官方文档支持的一次性无人值守模式）。

    仅在 live 闸门全部通过后才可能被构造；构造时还会再次核验产品版本。
    """

    name = "dsh-headless"

    def __init__(self, cfg, attempt_dir: Path, product: dict) -> None:
        super().__init__(cfg, attempt_dir)
        self.product = product

    def build(self, payload: dict, spec: dict) -> tuple[list[str], str, dict]:
        node = self.product["node_executable"]
        bin_js = self.product["bin_js"]
        # 启动器只解析自己的 flag，遇到第一个不认识的 token 就把后面全部交给 app。
        # 因此启动器 flag（--profile、--patch）必须在 app flag（--permission-mode 等）之前，
        # 否则 app 会收到 "unknown option '--patch'"。
        cmd = [node, bin_js, "--profile", "headless"]
        # payload / spec / 清单 meta 里的 command、args 一律不进入 argv。
        # --patch 只允许指向本项目 automation 内的无密钥覆盖文件（配置层已校验）。
        for rel in self.cfg.harness.patch_files:
            path = Path(rel)
            resolved = path if path.is_absolute() else (self.cfg.root / rel)
            cmd.extend(["--patch", str(resolved)])
        cmd.extend([
            "--permission-mode", self.cfg.harness.permission_mode,
            "--approval-policy", self.cfg.harness.approval_policy,
            "--json", "-",
        ])
        # 不传 --session-id：文档规定每次调用默认新建 session-<uuid>。
        # context 预算与 handoff 已在 worker 侧合成到 context_text 里。
        prompt = payload.get("context_text") or payload.get("task_text") or ""
        env = dict(os.environ)
        env["ELECTRON_RUN_AS_NODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return cmd, prompt, env

    def collect_receipt(self) -> str | None:
        """取回执文本。完成与否由 success_gate 决定，文本本身不能把失败改成成功。

        优先 RECEIPT.md。没有文件时，才用唯一一条 final.text。两份都有且去空白后不同，记为不一致。
        """
        self._stream_verdict = self._parse_stdout()
        file_text = ""
        receipt = self.attempt_dir / "RECEIPT.md"
        if receipt.exists():
            file_text = receipt.read_text(encoding="utf-8", errors="replace").strip()
        final_text = self._stream_verdict.get("text") or ""
        if file_text and final_text and file_text != final_text:
            self._stream_verdict["mismatch"] = True
        if file_text:
            return file_text
        return final_text or None

    def success_gate(self, exit_code: int | None, receipt_text: str | None) -> str | None:
        """官方契约：exit 0 且 final.reason.kind 严格为 completed，并有非空输出。"""
        if exit_code != 0:
            return None
        verdict = getattr(self, "_stream_verdict", None) or self._parse_stdout()
        if verdict.get("error"):
            return verdict["error"]
        if verdict.get("mismatch"):
            return "RECEIPT.md 与 final.text 不一致"
        if not (receipt_text and receipt_text.strip()):
            return "exit 0 且 completed，但没有有效任务输出"
        return None

    def _parse_stdout(self) -> dict:
        """严格解析 --json 事件流。任何歧义都 fail closed，不跳过坏行。"""
        empty = {"error": "无事件流", "text": "", "mismatch": False}
        log = self.attempt_dir / "harness.stdout.log"
        if not log.exists():
            return empty
        try:
            raw = log.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"error": "事件流不可读: %s" % exc, "text": "", "mismatch": False}
        finals = []
        for lineno, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return {"error": "事件流格式坏（第 %d 行不是 JSON）" % lineno,
                        "text": "", "mismatch": False}
            if not isinstance(event, dict):
                return {"error": "事件流格式坏（第 %d 行不是对象）" % lineno,
                        "text": "", "mismatch": False}
            if event.get("type") == "final":
                finals.append(event)
        if not finals:
            return {"error": "无 final 事件", "text": "", "mismatch": False}
        if len(finals) != 1:
            return {"error": "多条 final 事件，结果歧义（%d 条）" % len(finals),
                    "text": "", "mismatch": False}
        event = finals[0]
        reason = event.get("reason") if "reason" in event else None
        if not isinstance(reason, dict):
            return {"error": "final 缺少 reason", "text": "", "mismatch": False}
        kind = reason.get("kind")
        text = event.get("text")
        if text is None:
            text = ""
        if not isinstance(text, str):
            return {"error": "事件流格式坏（final.text 不是字符串）", "text": "", "mismatch": False}
        if not isinstance(kind, str) or kind != "completed":
            shown = kind if isinstance(kind, str) else "缺失"
            return {"error": "final.reason.kind 为 %s，不是 completed" % shown,
                    "text": text.strip(), "mismatch": False}
        return {"error": None, "text": text.strip(), "mismatch": False}


# ---------------------------------------------------------------- 产品核验

def probe_product(cfg) -> dict:
    """只读核验本机 Harness：产品版本 + 官方文档里的无人值守入口是否存在。

    不启动 profile、不发起模型调用、不连接设备。
    """
    from .common import read_json_file

    node = os.environ.get("DSH_NODE_EXECUTABLE", "")
    install = os.environ.get("DSH_INSTALL_DIR", "")
    result = {
        "node_executable": node,
        "install_dir": install,
        "bin_js": (install + "\\lib\\bin.js") if install else "",
        "version": None,
        "help_ok": False,
        "version_allowed": False,
        "errors": [],
    }
    if not node or not install:
        result["errors"].append("缺少 DSH_NODE_EXECUTABLE / DSH_INSTALL_DIR")
        return result
    if not os.path.exists(node):
        result["errors"].append("Harness 可执行文件不存在")
        return result

    def invoke(arg: str) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [node, result["bin_js"], arg],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120,
                env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"},
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except Exception as exc:  # noqa: BLE001
            return -1, "", str(exc)

    code, out, err = invoke("--version")
    if code == 0:
        result["version"] = out.strip().splitlines()[0].strip() if out.strip() else None
    else:
        result["errors"].append("dsh --version 失败: %s" % (err.strip()[:200] or code))

    code2, out2, err2 = invoke("--help")
    if code2 == 0:
        text = out2
        result["help_ok"] = ("headless" in text) and ("dsh headless" in text or "--profile headless" in text)
        if not result["help_ok"]:
            result["errors"].append("启动器帮助未包含 headless 入口")
    else:
        result["errors"].append("dsh --help 失败: %s" % (err2.strip()[:200] or code2))

    allowed = tuple(cfg.harness.product_version_allow or ())
    if result["version"] and allowed:
        result["version_allowed"] = result["version"] in allowed
        if not result["version_allowed"]:
            result["errors"].append("产品版本 %s 不在允许列表 %s" % (result["version"], list(allowed)))
    elif not allowed:
        result["errors"].append("配置未声明允许的产品版本")

    result["ok"] = bool(result["version"]) and result["help_ok"] and result["version_allowed"] \
        and not result["errors"]
    return result
