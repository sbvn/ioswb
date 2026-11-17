#!/usr/bin/env python3
"""离线测试套件。

覆盖任务要求的全部 mock 验证项：
- 新任务只执行一次；
- 重复扫描不重跑；
- 伪造任务 / 未可信清单被拒；
- 断网（推送失败）后只补传回执；
- STOP 三个时点（领取前 / 执行中 / 回执已存未上传）；
- 崩溃后的安全恢复（recovery_required + 人工 ack）；
- 并发第二个 worker 拿不到锁；
- 脱敏闸门拦截；
- 默认 dry-run、协议未就绪、仓库暂停标志、live 无信任规则时拒绝启动。

全程不连接手机、不访问网络（远端是本机临时 git 仓库）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback

from lab import AUTOMATION_ROOT, Lab

# 允许单跑某个用例时也能 import executor
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))

CLEAN_RECEIPT = """# MOCK 回执

- 任务：MOCK-001（离线测试）
- 结论：框架链路贯通
- 证据：本机 outbox 与 mock 执行日志
- 未涉及：手机、设备、注册、凭据
"""

TESTS: list = []


def test(fn):
    TESTS.append(fn)
    return fn


def check(condition, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def wait_for(predicate, timeout: float = 30.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def prepare(name: str, *, mode: str = "mock", task_id: str = "MOCK-001", revision: int = 1,
            scopes=("offline-testing",), mock=None, checked_out_remote: bool = False,
            body: str | None = None, pin: bool = True, content_override: str | None = None) -> Lab:
    lab = Lab(name, checked_out_remote=checked_out_remote)
    lab.plan_task(task_id, revision=revision, scopes=scopes, mock=mock, body=body,
                  content_override=content_override)
    lab.publish()
    if pin:
        lab.pin_manifest()
    lab.write_config(mode=mode)
    if not pin:
        lab.write_trust(pins=[])
    return lab


# ---------------------------------------------------------------- 用例

@test
def test_new_task_executes_once_and_uploads():
    lab = prepare("new_task_once", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "worker 退出码应为 0，实际 %s\n%s" % (proc.returncode, proc.stdout))
    check(lab.exec_starts() == 1, "应只执行 1 次，实际 %d" % lab.exec_starts())
    check(lab.remote_has("results/MOCK-001/r1/a1.md"), "回执应已推送到远端")
    ok = lab.events("attempt_upload_ok")
    check(len(ok) == 1, "应有 1 条 attempt_upload_ok")
    check(lab.outbox_files() == ["results/MOCK-001/r1/a1.md"],
          "outbox 应保留副本：%s" % lab.outbox_files())
    body = lab.remote_read("results/MOCK-001/r1/a1.md")
    check("MOCK 回执" in (body or ""), "远端回执内容不符合预期")


@test
def test_rescan_does_not_rerun():
    lab = prepare("rescan", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.run_worker("--once")
    before = lab.remote_commit_count()
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "重复扫描应正常退出")
    check(lab.exec_starts() == 1, "重复扫描不得重跑，实际执行 %d 次" % lab.exec_starts())
    check(lab.remote_commit_count() == before, "重复扫描不得产生新提交")


@test
def test_dry_run_has_no_side_effects():
    lab = prepare("dry_run", mode="dry-run", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "dry-run 应退出 0")
    check(lab.exec_starts() == 0, "dry-run 不得执行任务")
    check(lab.outbox_files() == [], "dry-run 不得写 outbox")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "dry-run 不得推送回执")
    check(len(lab.events("dry_run_plan")) == 1, "应记录一条 dry_run_plan")


@test
def test_untrusted_manifest_refused():
    lab = prepare("untrusted", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT}, pin=False)
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "未可信时应平稳等待")
    check(lab.exec_starts() == 0, "信任规则未配置时不得执行")
    check(len(lab.events("refused_untrusted")) == 1, "应记录 refused_untrusted")


@test
def test_forged_task_digest_refused():
    lab = prepare("forged", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT},
                  content_override="a" * 64)
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "伪造摘要应平稳拒绝")
    check(lab.exec_starts() == 0, "摘要不符时不得执行")
    check(len(lab.events("attempt_refused_integrity")) == 1, "应记录 attempt_refused_integrity")


@test
def test_scope_denied_refused():
    lab = prepare("scope", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT},
                  scopes=("phone-operation",))
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "越界范围应平稳拒绝")
    check(lab.exec_starts() == 0, "越界范围不得执行")
    check(len(lab.events("attempt_refused_scope")) == 1, "应记录 attempt_refused_scope")


@test
def test_content_change_stops_without_rerun():
    lab = prepare("content_change", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.run_worker("--once")
    check(lab.exec_starts() == 1, "首次应执行 1 次")
    # 同一编号同一版本，内容被改写
    lab.plan_task("MOCK-001", revision=1, body="# MOCK-001 被改写的任务\n\n内容已变化。\n")
    lab.publish()
    lab.pin_manifest()
    lab.write_config(mode="mock")
    proc = lab.run_worker("--once")
    check(proc.returncode == 4, "内容变化应停止并报告，实际 %s\n%s" % (proc.returncode, proc.stdout))
    check(lab.exec_starts() == 1, "内容变化后不得重跑")
    check(len(lab.events("content_changed")) == 1, "应记录 content_changed")


@test
def test_upload_failure_then_reupload_only():
    lab = prepare("offline_upload", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT},
                  checked_out_remote=True)
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "上传失败不应让 worker 崩溃\n%s" % proc.stdout)
    check(lab.exec_starts() == 1, "应执行 1 次")
    check(len(lab.events("attempt_result_saved")) == 1, "回执应先落本机")
    check(len(lab.events("attempt_upload_failed")) >= 1, "应记录上传失败")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "远端此时不应有回执")
    # 恢复推送能力后只补传
    lab.allow_push()
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 0, "补传应成功退出\n%s" % proc2.stdout)
    check(lab.exec_starts() == 1, "补传不得重新执行任务，实际 %d" % lab.exec_starts())
    check(lab.remote_has("results/MOCK-001/r1/a1.md"), "补传后远端应有回执")
    check(len(lab.events("attempt_upload_ok")) == 1, "应有 1 条 attempt_upload_ok")


@test
def test_stop_before_claim():
    lab = prepare("stop_before", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.stop("before claim")
    proc = lab.run_worker("--once")
    check(proc.returncode == 4, "STOP 时应退出 4，实际 %s" % proc.returncode)
    check(lab.exec_starts() == 0, "STOP 时不得领取/执行")
    check(len(lab.events("claim")) == 0, "STOP 时不得产生 claim")
    # 跨重启保留
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 4, "停止状态应跨重启保留")


@test
def test_stop_during_execution_cancels_and_confirms_exit():
    lab = prepare("stop_during", mock={"sleep_ms": 20000, "receipt": CLEAN_RECEIPT})
    worker = lab.start_worker("--once")
    try:
        check(wait_for(lambda: len(lab.events("child_started")) >= 1, timeout=45),
              "子进程应在超时内启动")
        lab.stop("during execution")
        proc_out, _ = worker.communicate(timeout=60)
    finally:
        if worker.poll() is None:
            worker.kill()
    check(worker.returncode == 4, "执行中停止应退出 4，实际 %s\n%s" % (worker.returncode, proc_out))
    cancelled = lab.events("attempt_cancelled")
    check(len(cancelled) == 1, "应记录 1 条 attempt_cancelled")
    check(cancelled[0].get("cancel_confirmed") is True, "必须确认子进程已退出")
    check(lab.exec_starts() == 1, "应只执行 1 次")
    check(lab.exec_ends() == 0, "被取消的执行不应产生回执")


@test
def test_stop_after_result_defers_upload_then_resume_uploads():
    lab = prepare("stop_after_result",
                  mock={"sleep_ms": 200, "receipt": CLEAN_RECEIPT, "stop_at_end": True})
    proc = lab.run_worker("--once")
    check(proc.returncode == 4, "回执已存但停止应退出 4，实际 %s\n%s" % (proc.returncode, proc.stdout))
    check(lab.exec_starts() == 1, "应执行 1 次")
    check(lab.outbox_files() == ["results/MOCK-001/r1/a1.md"], "回执应已原子落盘")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "停止时不得上传")
    check(len(lab.events("upload_deferred_by_stop")) == 1, "应记录 upload_deferred_by_stop")
    # 恢复后只补传
    r = lab.run_control("resume", "--confirm")
    check(r.returncode == 0, "resume 应成功：%s" % r.stdout)
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 0, "恢复后应正常退出\n%s" % proc2.stdout)
    check(lab.exec_starts() == 1, "恢复后不得重跑任务")
    check(lab.remote_has("results/MOCK-001/r1/a1.md"), "恢复后应补传回执")


@test
def test_crash_recovery_requires_ack():
    lab = prepare("crash", mock={"sleep_ms": 20000, "receipt": CLEAN_RECEIPT})
    worker = lab.start_worker("--once")
    check(wait_for(lambda: len(lab.events("child_started")) >= 1, timeout=45),
          "子进程应启动")
    worker.kill()          # 模拟崩溃：不给 finally 机会
    worker.wait(timeout=30)
    check(wait_for(lambda: lab.exec_ends() == 0, timeout=20), "被杀进程不应产出回执")
    proc = lab.run_worker("--once")
    check(proc.returncode == 5, "崩溃后应标记 recovery 并退出 5，实际 %s\n%s"
          % (proc.returncode, proc.stdout))
    check(len(lab.events("attempt_recovery_required")) == 1, "应记录 recovery_required")
    check(lab.exec_starts() == 1, "崩溃恢复不得自动重跑")
    # 人工 ack 之后仍然不重跑
    r = lab.run_control("ack", "MOCK-001@r1", "--note", "测试核查")
    check(r.returncode == 0, "ack 应成功：%s" % r.stdout)
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 0, "ack 后应正常等待，实际 %s" % proc2.returncode)
    check(lab.exec_starts() == 1, "ack 不得触发重跑")


@test
def test_second_worker_cannot_take_lock():
    lab = prepare("lock", mock={"sleep_ms": 20000, "receipt": CLEAN_RECEIPT})
    first = lab.start_worker("--once")
    try:
        check(wait_for(lambda: len(lab.events("child_started")) >= 1, timeout=45), "第一个 worker 应启动")
        second = lab.run_worker("--once")
        check(second.returncode == 3, "第二个 worker 应退出 3，实际 %s\n%s"
              % (second.returncode, second.stdout))
        check(lab.exec_starts() == 1, "不得出现第二次执行")
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=20)


@test
def test_redaction_quarantines_receipt():
    # 假样例按片段拼接，避免源码快照本身就带可被扫描器命中的字面量
    fake_udid = "DEADBEEF-" + "0123456789ABCDEF"
    fake_phone = "138" + "0013" + "8000"
    fake_path = "C:" + "\\" + "Users" + "\\" + "someone" + "\\" + "secret.txt"
    bad = ("# 回执\n\n设备 %s 已连接\n手机 %s\n路径 %s\n" % (fake_udid, fake_phone, fake_path))
    lab = prepare("redact", mock={"sleep_ms": 50, "receipt": bad})
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "命中脱敏规则应平稳处理\n%s" % proc.stdout)
    check(lab.exec_starts() == 1, "执行已发生")
    check(len(lab.events("attempt_quarantined")) == 1, "应记录 attempt_quarantined")
    check(lab.outbox_files() == [], "命中规则的正文不得进入 outbox")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "命中规则的正文不得上传")


@test
def test_protocol_not_ready_waits():
    lab = Lab("protocol_missing")
    lab.write_config(mode="mock")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "协议未就绪应平稳等待，实际 %s\n%s" % (proc.returncode, proc.stdout))
    check(len(lab.events("protocol_not_ready")) == 1, "应记录 protocol_not_ready")
    check(lab.exec_starts() == 0, "协议未就绪不得执行")


@test
def test_repo_pause_flag_stops():
    lab = prepare("pause_flag", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.set_pause_flag(True)
    proc = lab.run_worker("--once")
    check(proc.returncode == 4, "仓库暂停标志应导致退出 4，实际 %s\n%s" % (proc.returncode, proc.stdout))
    check(lab.exec_starts() == 0, "暂停期间不得执行")
    check(len(lab.events("pause_flag_observed")) == 1, "应记录 pause_flag_observed")


@test
def test_live_blocked_without_trust_rules():
    lab = prepare("live_blocked", mode="live", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT},
                  pin=False)
    proc = lab.run_worker("--once")
    check(proc.returncode == 2, "live 无信任规则应配置错误退出 2，实际 %s\n%s"
          % (proc.returncode, proc.stdout + proc.stderr))
    check("信任" in (proc.stdout + proc.stderr), "错误信息应说明信任规则缺失")
    check(lab.exec_starts() == 0, "闸门未通过不得执行")


@test
def test_control_status_reports_state():
    lab = prepare("status", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.run_worker("--once")
    proc = lab.run_control("status")
    check(proc.returncode == 0, "status 应成功：%s" % proc.stdout)
    payload = json.loads(proc.stdout)
    check(payload["lock_held"] is False, "已完成时锁应空闲")
    check(payload["stop_file_present"] is False, "不应有 STOP")
    check(payload["attempts"]["MOCK-001@r1"]["last"] == "attempt_upload_ok", "状态应为已上传")
    check("禁止据此抢锁" in payload["heartbeat_note"] or "心跳正常" in payload["heartbeat_note"],
          "心跳提示应包含禁止抢锁说明")


@test
def test_business_files_untouched():
    """执行器不得删除或改写业务目录下的既有脚本。"""
    from lab import AUTOMATION_ROOT

    business = AUTOMATION_ROOT.parent
    for name in ("weibo_browse.py", "weibo_browse_agent.js", "weibo_touch_agent.js",
                 "weibo_batch.py", "weibo_stability_probe.py", "weibo_min_agent.js",
                 "README.md", "AGENTS.md"):
        check((business / name).exists(), "业务文件缺失: %s" % name)


# ---------------------------------------------------------------- IOS-002 补测

PROTECTED_BUSINESS_FILES = (
    "weibo_browse.py", "weibo_browse_agent.js", "weibo_touch_agent.js",
    "weibo_batch.py", "weibo_min_agent.js", "weibo_stability_probe.py",
    "README.md", "AGENTS.md",
)


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@test
def test_protected_business_files_hash_unchanged():
    """执行前后比较哈希；只检查文件存在不算通过。"""
    from lab import AUTOMATION_ROOT

    business = AUTOMATION_ROOT.parent
    before = {name: _sha(business / name) for name in PROTECTED_BUSINESS_FILES}
    sizes = {name: (business / name).stat().st_size for name in PROTECTED_BUSINESS_FILES}
    lab = prepare("hash_guard", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.run_worker("--once")
    after = {name: _sha(business / name) for name in PROTECTED_BUSINESS_FILES}
    sizes_after = {name: (business / name).stat().st_size for name in PROTECTED_BUSINESS_FILES}
    changed = [name for name in before if before[name] != after[name]]
    check(not changed, "业务文件哈希发生变化: %s" % changed)
    check(sizes == sizes_after, "业务文件大小变化: %s" % sizes_after)
    check(all(before.values()), "哈希基线不得为空")


@test
def test_forged_receipt_does_not_trigger_next_task():
    """伪造的结果回执不得被当成领取凭证，也不得触发下一 revision。"""
    lab = prepare("forged_receipt", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.commit_remote_file("results/MOCK-001/r1/a1.md", "# 伪造回执\n\n并非本次执行产物。\n")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "伪造回执不应让 worker 失败\n%s" % proc.stdout)
    check(lab.exec_starts() == 1, "伪造回执不得替代领取：仍应执行 1 次，实际 %d" % lab.exec_starts())
    check(len(lab.events("claim")) == 1, "应只有 1 次 claim")
    # 伪造一个清单里不存在的 revision 回执
    lab.commit_remote_file("results/MOCK-001/r2/a1.md", "# 伪造 r2 回执\n")
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 0, "伪造 r2 回执不应改变 worker 行为\n%s" % proc2.stdout)
    check(lab.exec_starts() == 1, "伪造的 r2 回执不得触发执行，实际 %d" % lab.exec_starts())
    check(len(lab.events("claim")) == 1, "claim 数量不得增加")


@test
def test_trust_digest_pin_requires_commit_binding():
    """协议：摘要钉必须绑定到具体 commit，裸摘要不得单独放行。"""
    lab = prepare("trust_binding", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT}, pin=False)
    lab.pin_manifest(bound=False)
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "未绑定摘要应平稳等待")
    check(lab.exec_starts() == 0, "未绑定 commit 的摘要钉不得放行")
    refused = lab.events("refused_untrusted")
    check(refused, "应记录 refused_untrusted")
    reasons = " ".join(refused[0].get("reasons") or [])
    check("绑定" in reasons, "拒绝原因应说明缺少 commit 绑定：%s" % reasons)


@test
def test_crash_boundary_after_claim():
    lab = prepare("crash_claim", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    crashed = lab.run_worker("--once", extra_env={"IOSWB_FAULT_INJECT_PHASE": "after_claim"})
    check(crashed.returncode == 9, "应模拟崩溃退出 9，实际 %s" % crashed.returncode)
    check(lab.exec_starts() == 0, "领取后崩溃不得产生执行")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "重启应正常退出\n%s" % proc.stdout)
    check(len(lab.events("attempt_aborted_before_execution")) == 1,
          "领取后崩溃应记为 failed(abort)，不是 recovery")
    check(lab.protocol_states().get("MOCK-001@r1") == "failed", "协议状态应为 failed")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "不得上传不存在的回执")


@test
def test_crash_boundary_during_execution():
    lab = prepare("crash_exec", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    crashed = lab.run_worker("--once", extra_env={"IOSWB_FAULT_INJECT_PHASE": "executing"})
    check(crashed.returncode == 9, "应模拟崩溃退出 9")
    proc = lab.run_worker("--once")
    check(proc.returncode == 5, "执行中崩溃应要求人工恢复(5)，实际 %s\n%s"
          % (proc.returncode, proc.stdout))
    check(len(lab.events("attempt_recovery_required")) == 1, "应进入 recovery_required")
    check(lab.protocol_states().get("MOCK-001@r1") == "recovery_required", "协议状态应为 recovery_required")
    check(lab.exec_starts() == 0, "未 spawn 子进程时不得出现执行")
    proc2 = lab.run_worker("--once")
    check(proc2.returncode == 5, "未 ack 前不得继续")


@test
def test_crash_boundary_after_result_saved():
    lab = prepare("crash_saved", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    crashed = lab.run_worker("--once", extra_env={"IOSWB_FAULT_INJECT_PHASE": "after_result_saved"})
    check(crashed.returncode == 9, "应模拟崩溃退出 9")
    check(lab.exec_starts() == 1, "崩溃前应已执行 1 次")
    check(lab.outbox_files() == ["results/MOCK-001/r1/a1.md"], "回执应已落盘")
    check(not lab.remote_has("results/MOCK-001/r1/a1.md"), "崩溃时不应已上传")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "重启应只补传并正常退出\n%s" % proc.stdout)
    check(lab.exec_starts() == 1, "补传不得重新执行（执行次数仍为 1）")
    check(lab.remote_has("results/MOCK-001/r1/a1.md"), "重启后应补传成功")
    check(lab.protocol_states().get("MOCK-001@r1") == "succeeded", "补传后协议状态应为 succeeded")


@test
def test_crash_boundary_during_upload():
    lab = prepare("crash_upload", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    crashed = lab.run_worker("--once", extra_env={"IOSWB_FAULT_INJECT_PHASE": "uploading"})
    check(crashed.returncode == 9, "应模拟崩溃退出 9")
    check(lab.exec_starts() == 1, "崩溃前应已执行 1 次")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "重启应只补传\n%s" % proc.stdout)
    check(lab.exec_starts() == 1, "上传崩溃后不得重跑，执行次数仍为 1")
    check(lab.remote_has("results/MOCK-001/r1/a1.md"), "重启后应完成上传")
    check(len(lab.events("attempt_upload_ok")) == 1, "应恰好 1 条 upload_ok")


@test
def test_stop_across_restart_three_points():
    # 时点一：领取前
    lab1 = prepare("stop_restart_before", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab1.stop("before claim")
    check(lab1.run_worker("--once").returncode == 4, "领取前 STOP 应退出 4")
    check(lab1.run_worker("--once").returncode == 4, "重启后仍应退出 4")
    check(lab1.exec_starts() == 0, "时点一不得执行")

    # 时点二：执行中
    lab2 = prepare("stop_restart_during", mock={"sleep_ms": 20000, "receipt": CLEAN_RECEIPT})
    worker = lab2.start_worker("--once")
    try:
        check(wait_for(lambda: len(lab2.events("child_started")) >= 1, timeout=45), "子进程应启动")
        lab2.stop("during execution")
        worker.communicate(timeout=60)
    finally:
        if worker.poll() is None:
            worker.kill()
    check(worker.returncode == 4, "执行中 STOP 应退出 4")
    check(lab2.run_worker("--once").returncode == 4, "重启后停止状态应保留")
    check(lab2.exec_starts() == 1, "时点二不得重跑")

    # 时点三：回执已落盘、尚未上传
    lab3 = prepare("stop_restart_saved",
                   mock={"sleep_ms": 200, "receipt": CLEAN_RECEIPT, "stop_at_end": True})
    check(lab3.run_worker("--once").returncode == 4, "时点三应退出 4")
    check(lab3.outbox_files() == ["results/MOCK-001/r1/a1.md"], "回执应已落盘")
    check(not lab3.remote_has("results/MOCK-001/r1/a1.md"), "停止时不得上传")
    check(lab3.run_worker("--once").returncode == 4, "重启后仍应保持 stopped")
    check(not lab3.remote_has("results/MOCK-001/r1/a1.md"), "重启后仍不得上传")
    check(lab3.run_control("resume", "--confirm").returncode == 0, "resume 应成功")
    check(lab3.run_worker("--once").returncode == 0, "resume 后应只补传")
    check(lab3.exec_starts() == 1, "补传不得重跑")
    check(lab3.remote_has("results/MOCK-001/r1/a1.md"), "补传后远端应有回执")


@test
def test_handoff_persists_across_revisions():
    lab = prepare("handoff", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.run_worker("--once")
    record = lab.handoff("MOCK-001")
    check(record is not None, "应写出 handoff 文件")
    check(record.get("phase") == "succeeded", "handoff 终态应为 succeeded")
    lab.plan_task("MOCK-001", revision=2, body="# MOCK-001 r2\n\n第二版任务。\n",
                  mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab.publish()
    lab.pin_manifest()
    lab.write_config(mode="mock")
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "r2 应正常执行\n%s" % proc.stdout)
    check(lab.exec_starts() == 2, "r2 应产生第二次执行，实际 %d" % lab.exec_starts())
    composed = [e for e in lab.events("context_composed") if e.get("attempt") == "MOCK-001@r2"]
    check(composed, "应记录 r2 的 context_composed")
    check(composed[0]["handoff_present"] is True, "r2 的上下文应带上一次 handoff")
    check(composed[0]["handoff_phase"] == "succeeded", "handoff 应来自 r1 的成功终态")
    spec = lab.harness_spec("MOCK-001@r2")
    check(spec is not None and spec.get("handoff"), "新会话的 spec 应包含 handoff")
    check(spec["handoff"].get("phase") == "succeeded", "spec 内 handoff 阶段应为 succeeded")


@test
def test_context_budget_trims_oversized_task():
    big = "# 大任务\n\n" + ("A" * 20000) + "\n"
    lab = prepare("context_budget", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT}, body=big)
    lab.write_config(mode="mock", limits={
        "max_attempts_per_revision": 1, "upload_retries": 2, "task_timeout_seconds": 60,
        "cancel_grace_seconds": 5, "scan_inflight_seconds": 1, "context_budget_bytes": 4096,
    })
    proc = lab.run_worker("--once")
    check(proc.returncode == 0, "超预算任务应被截断后执行\n%s" % proc.stdout)
    composed = lab.events("context_composed")
    check(composed, "应记录 context_composed")
    meta = composed[0]
    check(meta["trimmed"] is True, "应标记 trimmed")
    check(meta["within_budget"] is True, "拼接后的 prompt 不得超过预算")
    check(meta["prompt_bytes"] <= 4096, "prompt 字节数 %d 超预算" % meta["prompt_bytes"])
    check(meta["task_bytes"] > meta["kept_task_bytes"], "原文应大于保留部分")
    check(lab.exec_starts() == 1, "截断后仍应执行一次")


@test
def test_ledger_six_protocol_states():
    from executor.ledger import PROTOCOL_STATES, STATE_MAP

    check(set(PROTOCOL_STATES) == {"accepted", "running", "succeeded", "failed",
                                   "stopped", "recovery_required"}, "六状态定义不符")
    check(STATE_MAP.get("claim") == "accepted", "claim 应映射 accepted")
    check(STATE_MAP.get("attempt_start") == "running", "attempt_start 应映射 running")

    observed = set()
    lab_ok = prepare("states_ok", mock={"sleep_ms": 50, "receipt": CLEAN_RECEIPT})
    lab_ok.run_worker("--once")
    observed.add(lab_ok.protocol_states()["MOCK-001@r1"])

    lab_fail = prepare("states_fail", mock={"sleep_ms": 50,
                                            "receipt": "设备 " + "DEADBEEF-" + "0123456789ABCDEF\n"})
    lab_fail.run_worker("--once")
    observed.add(lab_fail.protocol_states()["MOCK-001@r1"])

    lab_stop = prepare("states_stop", mock={"sleep_ms": 200, "receipt": CLEAN_RECEIPT,
                                            "stop_at_end": True})
    lab_stop.run_worker("--once")
    observed.add(lab_stop.protocol_states()["MOCK-001@r1"])

    lab_rec = prepare("states_recovery", mock={"sleep_ms": 8000, "receipt": CLEAN_RECEIPT})
    lab_rec.write_config(mode="mock", limits={
        "max_attempts_per_revision": 1, "upload_retries": 2, "task_timeout_seconds": 2,
        "cancel_grace_seconds": 3, "scan_inflight_seconds": 1, "context_budget_bytes": 48000,
    })
    lab_rec.run_worker("--once")
    observed.add(lab_rec.protocol_states()["MOCK-001@r1"])

    check(observed == {"succeeded", "failed", "stopped", "recovery_required"},
          "可观测终态应为四个，实际 %s" % sorted(observed))
    # accepted / running 是过程态，由映射表与台账事件覆盖
    events = {r.get("event") for r in lab_ok.ledger()}
    check("claim" in events and "attempt_start" in events, "台账应包含 accepted/​running 对应事件")


# ---------------------------------------------------------------- 运行器

def main(argv: list[str]) -> int:
    only = argv[1] if len(argv) > 1 else None
    selected = [t for t in TESTS if not only or only in t.__name__]
    print("=" * 72)
    print("IOSWB automation 离线测试：%d 个用例" % len(selected))
    print("=" * 72)
    failures = []
    started = time.time()
    for fn in selected:
        begin = time.time()
        try:
            fn()
            print("PASS  %-52s %5.1fs" % (fn.__name__, time.time() - begin))
        except Exception as exc:  # noqa: BLE001
            failures.append((fn.__name__, exc))
            print("FAIL  %-52s %5.1fs" % (fn.__name__, time.time() - begin))
            print("      %s" % str(exc).replace("\n", "\n      ")[:1200])
            traceback.print_exc()
    print("-" * 72)
    print("通过 %d / %d，用时 %.1fs" % (len(selected) - len(failures), len(selected), time.time() - started))
    if failures:
        print("失败用例：")
        for name, exc in failures:
            print("  - %s: %s" % (name, str(exc).splitlines()[0][:160]))
        return 1
    print("全部通过（离线 mock；未连接手机、未访问网络）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
