"""单 worker / 单任务调度状态机（IOS-002 协议对齐版）。

不变量：
- 只有持有 OS 排他锁的进程能进入循环；第二个 worker 直接退出（exit 3）。
- 同一 (task_id, revision) 只执行一次 —— 这是 **at-most-once**，不是 exactly-once；
  崩溃时宁可没有回执，也不重跑。
- 领取前必须：清单可信、任务内容摘要匹配、范围在批准清单内。
- 持续入口另要求本机 permits.json 写明任务、版本、范围、预算和期限。
- STOP（本机文件或仓库暂停标志）在三个时点生效；只有确认子进程退出才记 stopped。
- 回执先原子落本机 spool，再上传；上传失败只重传。
- 结果不明 → recovery_required，等人核查，不自动续跑。
- 每个任务一个新会话；会话可换新，handoff 落盘跨尝试保存；输入受 context 预算约束。
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from .common import (
    ConfigError,
    GitError,
    ManifestError,
    ScopeError,
    TrustError,
    atomic_write_text,
    ensure_dir,
    now_iso,
    sha256_bytes,
    sha256_text,
)
from .config import Config
from .gitrepo import RepoCache
from .handoff import HandoffStore, compose_context
from .ledger import (
    EXIT_CONFIG,
    EXIT_ERROR,
    EXIT_LOCKED,
    EXIT_OK,
    EXIT_RECOVERY,
    EXIT_STOPPED,
    NEEDS_REVIEW,
    TERMINAL,
    Ledger,
    attempt_key,
)
from .locking import ProcessLock
from .manifest import TaskEntry, parse_manifest, verify_task_binding
from .redact import scan as scan_receipt
from .runner import HeadlessRunner, MockRunner, probe_product
from .sigverify import verify_commit_signature
from .trust import evaluate_manifest, evaluate_task
from .trust import load_trust

# 落盘后可以安全补传的状态（崩溃在这里不需要 recovery_required）。
RESUMABLE_UPLOAD = ("attempt_result_saved", "attempt_upload_failed", "upload_deferred_by_stop")

# 仅测试用的故障注入点（环境变量控制，生产不会设置）。用于确定性地覆盖四个崩溃边界。
FAULT_ENV = "IOSWB_FAULT_INJECT_PHASE"


def _fault(phase: str) -> None:
    if os.environ.get(FAULT_ENV) == phase:
        os._exit(9)


class Worker:
    def __init__(self, cfg: Config, *, mode: str | None = None, once: bool = False,
                 max_cycles: int = 0, require_permit: bool = False,
                 out: Callable[[str], None] = print) -> None:
        self.cfg = cfg
        self.mode = mode or cfg.mode
        self.once = once
        self.max_cycles = max_cycles
        self.require_permit = require_permit
        self.out = out
        self.ledger = Ledger(cfg.ledger_path)
        self.lock = ProcessLock(cfg.lock_path)
        self.repo = RepoCache(cfg.work_dir, cfg.repo_url, cfg.repo_branch)
        self.product: dict = {}
        self._pause_seen_at: str | None = None
        self._child_pid: int | None = None
        self._ledger_corrupt = False

    # ------------------------------------------------------------ 入口

    def run(self) -> int:
        cfg = self.cfg
        cfg.ensure_dirs()
        if not self.lock.acquire():
            self.out("[锁] 已有另一个 worker 持有排他锁，本进程退出（不抢锁、不重跑）。")
            return EXIT_LOCKED
        exit_code = EXIT_OK
        try:
            self.ledger.load()
            if self.ledger.corrupt_reason:
                self._ledger_corrupt = True
                self.out("[台账] %s" % self.ledger.corrupt_reason)
                exit_code = EXIT_ERROR
                return exit_code
            self.product = probe_product(cfg) if self.mode == "live" else {}
            self._write_worker_state("running")
            self._recovery_sweep()
            blocked = [k for k, v in self.ledger.attempts().items()
                       if v["last"] == "attempt_recovery_required"]
            if blocked:
                self.ledger.append("worker_blocked_recovery", attempts=sorted(blocked))
                self.out("[恢复] 存在结果不明的 attempt（%s）：等待人工核查后再启动。"
                         % ", ".join(sorted(blocked)))
                return EXIT_RECOVERY
            self.ledger.append("worker_start", mode=self.mode, branch=cfg.repo_branch,
                               config=str(cfg.path))
            cycles = 0
            while True:
                cycles += 1
                verdict = self.cycle()
                if verdict == "stopped":
                    exit_code = EXIT_STOPPED
                    break
                if verdict == "recovery":
                    exit_code = EXIT_RECOVERY
                    break
                if self.once or (self.max_cycles and cycles >= self.max_cycles):
                    break
                self._sleep(cfg.poll_interval_seconds)
                if self._stop_requested():
                    self.ledger.append("stop_observed", phase="sleep")
                    exit_code = EXIT_STOPPED
                    break
            if exit_code == EXIT_STOPPED:
                self.ledger.append("worker_stopped", reason=self._stop_reason())
        except ConfigError as exc:
            self.out("[配置] %s" % exc)
            exit_code = EXIT_CONFIG
        except (ManifestError, TrustError, GitError, ScopeError) as exc:
            self.out("[错误] %s" % exc)
            exit_code = EXIT_ERROR
        finally:
            self._write_worker_state("stopped" if exit_code == EXIT_STOPPED else "idle")
            if not self._ledger_corrupt:
                self.ledger.append("worker_stop", exit_code=exit_code)
            self.lock.release()
        return exit_code

    # ------------------------------------------------------------ 一个周期

    def cycle(self) -> str:
        cfg = self.cfg
        self._heartbeat("waiting")
        # 1) 最优先：停止标志
        if self._stop_requested():
            self.ledger.append("stop_observed", phase="cycle_start", reason=self._stop_reason())
            self.out("[停止] %s：不领取新任务。" % self._stop_reason())
            return "stopped"

        # 2) 先补传未上传的回执（绝不重新执行任务）
        if self._retry_pending_uploads() == "stopped":
            return "stopped"

        # 3) 读取远端分支与清单
        try:
            head = self.repo.fetch()
        except GitError as exc:
            self._record_once("scan_failed", "fetch", error=str(exc)[:400])
            self.out("[扫描] 拉取分支失败：%s" % str(exc)[:200])
            return "wait"
        self.ledger.append("manifest_head", head=head[:12])

        # 4) 仓库暂停标志
        if self.cfg.pause_flag_path and self.repo.file_exists(head, cfg.pause_flag_path):
            self._pause_seen_at = head
            self.ledger.append("pause_flag_observed", path=cfg.pause_flag_path, head=head[:12])
            self.out("[暂停] 仓库暂停标志存在：%s" % cfg.pause_flag_path)
            return "stopped"

        # 5) 读清单
        if not self.repo.file_exists(head, cfg.manifest_path):
            self._record_once("protocol_not_ready", "manifest_missing",
                              path=cfg.manifest_path, head=head[:12])
            self.out("[协议] 分支上没有 %s：发布协议未就绪，继续等待。" % cfg.manifest_path)
            return "wait"
        try:
            manifest_bytes = self.repo.read_file(head, cfg.manifest_path)
            manifest = parse_manifest(manifest_bytes)
        except (GitError, ManifestError) as exc:
            self._record_once("manifest_invalid", "invalid", error=str(exc)[:400], head=head[:12])
            self.out("[协议] 清单不可用：%s" % str(exc)[:200])
            return "wait"

        # 6) 信任核验（r2：清单级与任务级分开判定）
        # 清单级：摘要钉 / 清单提交钉 / 清单提交的签名。
        manifest_commit = self.repo.file_commit(head, cfg.manifest_path) or head
        trust_cfg = load_trust(cfg.trust_file)
        published = manifest.published()
        # SSH 签名核验（不是 %G?=N 就放行）：用本机钉住的公钥 / 身份 / 指纹
        manifest_signature = None
        if manifest_commit:
            manifest_signature = verify_commit_signature(
                self.repo.ensure_clone(), manifest_commit, trust_cfg.signers,
                repo_url=cfg.repo_url, ref=cfg.repo_branch).as_dict()
        manifest_decision = evaluate_manifest(
            trust_cfg,
            manifest_sha256=manifest.raw_sha256,
            manifest_commit=manifest_commit,
            manifest_signature=manifest_signature,
        )
        # 任务级：清单级不成立时，只放行被单独钉住 task_commit 的那一个任务。
        decisions = {
            entry.key: evaluate_task(trust_cfg, task_commit=entry.task_commit,
                                     manifest_decision=manifest_decision)
            for entry in published
        }
        permit_set = None
        if self.require_permit:
            from .permit import load_permits

            permit_set = load_permits(self.cfg.root / "config" / "permits.json")
            if permit_set.blocked:
                self._record_once("permit_blocked", permit_set.blocked[:120],
                                  reason=permit_set.blocked)
                self.out("[许可] %s" % permit_set.blocked)
                return "wait"

        trusted_any = any(d.trusted for d in decisions.values())
        if not trusted_any:
            self._record_once("refused_untrusted", "trust:" + manifest.raw_sha256[:12],
                              reasons=manifest_decision.reasons,
                              manifest_sha256=manifest.raw_sha256,
                              manifest_commit=manifest_commit)
            self.out("[信任] 拒绝：%s" % manifest_decision.summary())
            if self.mode != "dry-run":
                return "wait"
        else:
            self.ledger.append("trust_ok", rule=manifest_decision.rule,
                               scope=manifest_decision.scope,
                               manifest_sha256=manifest.raw_sha256,
                               trusted_tasks=sorted(k for k, d in decisions.items() if d.trusted))

        # 7) 记录本周期内未获授权的任务（每个任务一条，去重；不静默跳过）
        for entry in published:
            key = attempt_key(entry.task_id, entry.revision)
            if decisions[key].trusted:
                continue
            if self.ledger.has_event_any(key, ("task_not_trusted",)):
                continue
            self.ledger.append("task_not_trusted", attempt=key, task_id=entry.task_id,
                               revision=entry.revision, task_commit=entry.task_commit,
                               reasons=decisions[key].reasons,
                               note="未单独钉住该 task_commit，且清单级信任不成立")
            self.out("[信任] %s 未获授权（不放行同一清单里的其他任务）。" % key)

        # 8) 选一个任务
        for entry in sorted(published, key=lambda t: (t.task_id, t.revision)):
            key = attempt_key(entry.task_id, entry.revision)
            decision = decisions[key]
            recorded = self.ledger.digest_of(key)
            if recorded and recorded != entry.content_sha256:
                self.ledger.append("content_changed", attempt=key,
                                   recorded_digest=recorded, manifest_digest=entry.content_sha256,
                                   action="stop_and_report")
                self.out("[停止] %s 的内容与已领取时不同，停止并等待人工核查。" % key)
                return "stopped"
            if self.ledger.has_claim(key):
                continue
            if self.ledger.has_event_any(key, ("attempt_refused_scope", "attempt_refused_integrity")):
                continue
            if self.ledger.is_closed(key):
                continue
            if not decision.trusted:
                continue
            if permit_set is not None:
                allowed, why = permit_set.allows(entry, self.ledger)
                if not allowed:
                    self._record_once("permit_denied", entry.key, attempt=entry.key,
                                      task_id=entry.task_id, revision=entry.revision,
                                      reason=why)
                    self.out("[许可] %s：%s" % (entry.key, why))
                    continue

            ok, reason, task_bytes = verify_task_binding(entry, self.repo, head)
            if not ok:
                self.ledger.append("attempt_refused_integrity", attempt=key,
                                   task_id=entry.task_id, revision=entry.revision,
                                   digest=entry.content_sha256, reason=reason)
                self.out("[完整性] %s 拒绝：%s" % (key, reason))
                continue

            try:
                self._scope_gate(entry, task_bytes.decode("utf-8", errors="replace"))
            except ScopeError as exc:
                self.ledger.append("attempt_refused_scope", attempt=key, task_id=entry.task_id,
                                   revision=entry.revision, digest=entry.content_sha256,
                                   reason=str(exc), scopes=list(entry.scopes))
                self.out("[范围] %s 拒绝：%s" % (key, exc))
                continue

            if self.mode == "dry-run":
                self.ledger.append("dry_run_plan", attempt=key, task_id=entry.task_id,
                                   revision=entry.revision, digest=entry.content_sha256,
                                   scopes=list(entry.scopes), trusted=True,
                                   trust_rule=decision.rule, trust_scope=decision.scope,
                                   next_step="would_claim_and_execute")
                self.out("[dry-run] 将领取 %s（摘要 %s，范围 %s，信任 %s/%s），不执行。"
                         % (key, entry.content_sha256[:12], ",".join(entry.scopes),
                            decision.rule, decision.scope))
                return "wait"

            return self._execute(entry, task_bytes, decision)
        return "wait"

    # ------------------------------------------------------------ 范围闸门

    # 任务正文里出现这些词时给出提示（仅提示）。范围硬闸门只看清单的 scopes：
    # 清单可信 + scopes 批准才是授权来源；用词法否决会误伤正常任务（例如正文写“不注册”）。
    _DENIED_TEXT_HINTS = (
        "连接手机", "附加 app", "attach", "spawn", "kill", "真实触摸", "点击", "滑动",
        "注册", "验证码", "aid", "useruid", "usergsid", "安装工具", "跑批次",
    )

    def _scope_gate(self, entry: TaskEntry, task_text: str) -> None:
        if not entry.scopes:
            raise ScopeError("任务未声明范围")
        always = [s for s in entry.scopes if s in self.cfg.denied_scopes]
        if always:
            raise ScopeError("声明了禁止范围: %s" % ", ".join(always))
        outside = [s for s in entry.scopes if s not in self.cfg.allowed_scopes]
        if outside:
            raise ScopeError("范围不在本机批准清单内: %s（允许 %s）"
                             % (", ".join(outside), ", ".join(self.cfg.allowed_scopes)))
        text = (task_text or "").lower()
        hits = [hint for hint in self._DENIED_TEXT_HINTS if hint.lower() in text]
        if hits:
            self.ledger.append("scope_text_warning", attempt=entry.key, hints=hits,
                               note="仅提示：范围以清单 scopes 为准；执行器不执行手机操作")

    # ------------------------------------------------------------ 执行

    def _handoff(self, task_id: str) -> HandoffStore:
        return HandoffStore(self.cfg.handoff_dir, task_id)

    def _execute(self, entry: TaskEntry, task_bytes: bytes, decision) -> str:
        cfg = self.cfg
        key = attempt_key(entry.task_id, entry.revision)
        attempt = 1
        attempt_dir = cfg.attempts_dir / ("%s-a%d" % (key.replace("@", "_"), attempt))
        ensure_dir(attempt_dir)
        task_text = task_bytes.decode("utf-8", errors="replace")

        if self._stop_requested():
            self.ledger.append("stop_observed", phase="before_claim", attempt=key)
            return "stopped"

        # 新会话的输入：持久 handoff + context 预算
        store = self._handoff(entry.task_id)
        previous = store.load()
        context_text, context_meta = compose_context(
            task_text, previous, cfg.limits.context_budget_bytes)
        self.ledger.append("context_composed", attempt=key, **context_meta)

        self.ledger.append("claim", attempt=key, task_id=entry.task_id,
                           revision=entry.revision, digest=entry.content_sha256,
                           scopes=list(entry.scopes), trust_rule=decision.rule,
                           trust_scope=decision.scope,
                           mode=self.mode, context=context_meta)
        store.save(revision=entry.revision, attempt=attempt, phase="accepted",
                   digest=entry.content_sha256, summary="已领取，尚未开始执行",
                   ledger_seq=self.ledger.records[-1]["seq"])
        self.ledger.append("attempt_phase", attempt=key, phase="accepted")
        _fault("after_claim")
        self.ledger.append("attempt_start", attempt=key, task_id=entry.task_id,
                           revision=entry.revision, digest=entry.content_sha256,
                           attempt_dir=str(attempt_dir))

        if self.mode == "mock":
            runner = MockRunner(cfg, attempt_dir)
        elif self.mode == "live":
            if not self.product.get("ok"):
                self.ledger.append("attempt_failed", attempt=key, reason="unattended_entry_unverified",
                                   product=self._product_summary())
                store.save(revision=entry.revision, attempt=attempt, phase="failed",
                           digest=entry.content_sha256, summary="真实入口未核实，未执行")
                self.out("[阻塞] 真实入口未核实通过，拒绝执行。")
                return "wait"
            runner = HeadlessRunner(cfg, attempt_dir, self.product)
        else:
            raise ConfigError("未知模式: %s" % self.mode)

        spec = dict(entry.meta.get("mock_harness") or {}) if self.mode == "mock" else {}
        spec.pop("command", None)
        spec.pop("args", None)
        spec["stop_file"] = str(cfg.stop_path)

        payload = {
            "task_id": entry.task_id,
            "revision": entry.revision,
            "task_text": task_text,
            "context_text": context_text,
            "context": context_meta,
            "handoff": previous,
        }

        self.ledger.append("attempt_phase", attempt=key, phase="executing")
        store.save(revision=entry.revision, attempt=attempt, phase="running",
                   digest=entry.content_sha256, summary="执行中（独立新会话）",
                   ledger_seq=self.ledger.records[-1]["seq"])
        _fault("executing")

        outcome = runner.run(
            payload,
            spec,
            timeout=min(cfg.limits.task_timeout_seconds, cfg.harness.timeout_seconds),
            should_cancel=self._stop_requested,
            heartbeat=self._heartbeat,
            on_child=self._on_child,
        )
        self.ledger.append("attempt_harness_exit", attempt=key, **outcome.as_dict())

        if outcome.status == "cancelled":
            if not outcome.cancel_confirmed:
                # 协议：未确认退出时不得记 stopped，保持 recovery_required。
                self.ledger.append("attempt_recovery_required", attempt=key,
                                   reason="cancel_unconfirmed",
                                   note="无法确认子进程已退出，结果不明")
                store.save(revision=entry.revision, attempt=attempt, phase="recovery_required",
                           digest=entry.content_sha256, summary="停止时无法确认子进程退出")
                self.out("[恢复] %s 取消未能确认退出，标记 recovery_required。" % key)
                return "recovery"
            self.ledger.append("attempt_cancelled", attempt=key,
                               cancel_confirmed=True,
                               note="取消即消耗该版本；如需继续请发布新 revision 并人工 ack")
            store.save(revision=entry.revision, attempt=attempt, phase="stopped",
                       digest=entry.content_sha256, summary="执行中被 STOP 取消，子进程已确认退出")
            self.out("[停止] %s 的执行子进程已确认退出（cancel_confirmed=True）。" % key)
            return "stopped"
        if outcome.status == "timeout":
            self.ledger.append("attempt_recovery_required", attempt=key,
                               reason="timeout", note="结果不明，等待人工核查")
            store.save(revision=entry.revision, attempt=attempt, phase="recovery_required",
                       digest=entry.content_sha256, summary="执行超时，结果不明")
            self.out("[恢复] %s 超时，标记 recovery_required。" % key)
            return "recovery"
        if outcome.status in ("failed", "unreachable"):
            self.ledger.append("attempt_failed", attempt=key, reason=outcome.status,
                               error=outcome.error[:600])
            store.save(revision=entry.revision, attempt=attempt, phase="failed",
                       digest=entry.content_sha256, summary="执行失败：%s" % outcome.status)
            self.out("[失败] %s 执行失败：%s" % (key, (outcome.error or outcome.status)[:200]))
            return "wait"

        return self._handle_success(entry, key, attempt, outcome, context_meta)

    def _handle_success(self, entry: TaskEntry, key: str, attempt: int, outcome,
                        context_meta: dict) -> str:
        cfg = self.cfg
        store = self._handoff(entry.task_id)
        text = outcome.receipt_text or ""
        if not text.strip():
            self.ledger.append("attempt_failed", attempt=key, reason="empty_receipt")
            store.save(revision=entry.revision, attempt=attempt, phase="failed",
                       digest=entry.content_sha256, summary="执行成功但回执为空")
            return "wait"

        findings = scan_receipt(text)
        if findings:
            quarantine = cfg.quarantine_dir / ("%s-a%d.md" % (key.replace("@", "_"), attempt))
            atomic_write_text(quarantine, text)
            self.ledger.append("attempt_quarantined", attempt=key,
                               findings=[f.as_dict() for f in findings][:20],
                               quarantine_path=str(quarantine.relative_to(cfg.root)))
            store.save(revision=entry.revision, attempt=attempt, phase="failed",
                       digest=entry.content_sha256, summary="回执命中脱敏规则，已隔离")
            self.out("[脱敏] %s 的回执命中 %d 条禁止规则，已隔离，不上传。" % (key, len(findings)))
            return "wait"

        rel = cfg.result_rel_path(entry.task_id, entry.revision, attempt)
        meta_rel = rel[:-3] + ".meta.json" if rel.endswith(".md") else rel + ".meta.json"
        outbox_path = cfg.outbox_dir / rel
        meta_path = cfg.outbox_dir / meta_rel
        atomic_write_text(outbox_path, text)
        meta = self._receipt_meta(entry, attempt, outcome, rel, sha256_text(text))
        meta_text = json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        atomic_write_text(meta_path, meta_text)
        receipt_digest = sha256_text(text)
        self.ledger.append("attempt_phase", attempt=key, phase="result_saved")
        self.ledger.append("attempt_result_saved", attempt=key, rel_path=rel,
                           meta_rel_path=meta_rel,
                           receipt_sha256=receipt_digest,
                           meta_sha256=sha256_text(meta_text),
                           outbox=str(outbox_path.relative_to(cfg.root)),
                           context=context_meta)
        store.save(revision=entry.revision, attempt=attempt, phase="running",
                   digest=entry.content_sha256, receipt_rel_path=rel,
                   summary="回执已原子落盘，尚未上传",
                   ledger_seq=self.ledger.records[-1]["seq"])
        self.out("[回执] 已原子落盘：%s" % outbox_path.relative_to(cfg.root))
        _fault("after_result_saved")

        if self._stop_requested():
            self.ledger.append("upload_deferred_by_stop", attempt=key, rel_path=rel)
            store.save(revision=entry.revision, attempt=attempt, phase="stopped",
                       digest=entry.content_sha256, receipt_rel_path=rel,
                       summary="STOP：回执已落盘但未上传，恢复后只补传")
            self.out("[停止] 回执已保存但未上传；恢复后只补传，不重跑。")
            return "stopped"

        return self._upload(key, rel, text, meta_text, meta_rel, entry)

    def _receipt_meta(self, entry: TaskEntry, attempt: int, outcome, rel: str,
                      receipt_sha256: str) -> dict:
        kind = "missing"
        if outcome.stdout_path:
            final_path = Path(outcome.stdout_path).parent / "final.json"
            try:
                event = json.loads(final_path.read_text(encoding="utf-8"))
                reason = event.get("reason") if isinstance(event, dict) else None
                if isinstance(reason, dict) and isinstance(reason.get("kind"), str):
                    kind = reason["kind"]
            except (OSError, json.JSONDecodeError):
                kind = "unreadable"
        return {
            "schema": "ioswb-receipt-meta/1",
            "task_id": entry.task_id,
            "revision": entry.revision,
            "attempt": attempt,
            "runner": self.mode,
            "exit_code": outcome.exit_code,
            "status": outcome.status,
            "final_reason_kind": kind,
            "marker_ok": outcome.status == "success" and kind == "completed",
            "duration_seconds": round(outcome.duration_seconds, 3),
            "receipt_sha256": receipt_sha256,
            "raw_rel_path": rel,
            "saved_login": False,
        }

    def _upload(self, key: str, rel: str, text: str, meta_text: str, meta_rel: str,
                entry: TaskEntry) -> str:
        cfg = self.cfg
        payload = text.encode("utf-8")
        meta_payload = meta_text.encode("utf-8")
        digest = sha256_bytes(payload)
        meta_digest = sha256_bytes(meta_payload)
        store = self._handoff(entry.task_id)
        self.ledger.append("attempt_phase", attempt=key, phase="uploading")
        _fault("uploading")

        # 幂等：远端两份文件都已是同内容时，不再新建提交。
        try:
            head = self.repo.fetch()
            raw_same = self.repo.file_exists(head, rel) and sha256_bytes(
                self.repo.read_file(head, rel)) == digest
            meta_same = self.repo.file_exists(head, meta_rel) and sha256_bytes(
                self.repo.read_file(head, meta_rel)) == meta_digest
            if raw_same and meta_same:
                self.ledger.append("upload_duplicate_skipped", attempt=key, rel_path=rel,
                                   meta_rel_path=meta_rel, commit=head)
                self.ledger.append("attempt_upload_ok", attempt=key, rel_path=rel,
                                   meta_rel_path=meta_rel, commit=head, skipped_duplicate=True)
                store.save(revision=entry.revision, attempt=1, phase="succeeded",
                           digest=entry.content_sha256, receipt_rel_path=rel,
                           summary="远端已有同内容回执，未重复提交")
                self.out("[上传] 远端已有同内容回执，跳过重复提交（%s）。" % rel)
                return "wait"
        except GitError:
            pass

        message = "自动回执 %s r%d a1：%s" % (
            entry.task_id, entry.revision, entry.title or "任务结果",
        )
        result = self.repo.commit_and_push_files(
            [(rel, payload), (meta_rel, meta_payload)], message,
            retries=cfg.limits.upload_retries,
        )
        if result["status"] == "pushed":
            self.ledger.append("attempt_upload_ok", attempt=key, rel_path=rel,
                               meta_rel_path=meta_rel,
                               commit=result["commit"], push_attempts=result.get("attempts"))
            store.save(revision=entry.revision, attempt=1, phase="succeeded",
                       digest=entry.content_sha256, receipt_rel_path=rel,
                       summary="回执已上传", ledger_seq=self.ledger.records[-1]["seq"])
            self.out("[上传] %s -> %s（commit %s）" % (rel, cfg.repo_branch, result["commit"][:12]))
            return "wait"
        self.ledger.append("attempt_upload_failed", attempt=key, rel_path=rel,
                           error=result.get("error", "")[:600],
                           note="只重传回执，不重新执行任务")
        store.save(revision=entry.revision, attempt=1, phase="running",
                   digest=entry.content_sha256, receipt_rel_path=rel,
                   summary="上传失败，回执待补传")
        self.out("[上传] 失败，已保留待传回执；稍后只重传。")
        return "wait"

    # ------------------------------------------------------------ 补传

    def _is_resumable_upload(self, key: str, slot: dict) -> bool:
        if slot["last"] in RESUMABLE_UPLOAD:
            return True
        if slot["last"] == "attempt_phase":
            for record in reversed(self.ledger.records):
                if record.get("attempt") == key and record.get("event") == "attempt_phase":
                    return record.get("phase") in ("result_saved", "uploading")
        return False

    def _retry_pending_uploads(self) -> str:
        attempts = self.ledger.attempts()
        for key, slot in sorted(attempts.items()):
            if not self._is_resumable_upload(key, slot):
                continue
            saved = None
            for record in reversed(self.ledger.records):
                if record.get("attempt") == key and record.get("event") == "attempt_result_saved":
                    saved = record
                    break
            if not saved:
                continue
            rel = saved.get("rel_path")
            meta_rel = saved.get("meta_rel_path")
            outbox_path = self.cfg.outbox_dir / rel
            if not outbox_path.exists() or not meta_rel:
                self.ledger.append("upload_missing_outbox", attempt=key, rel_path=rel)
                continue
            meta_path = self.cfg.outbox_dir / meta_rel
            if not meta_path.exists():
                self.ledger.append("upload_missing_outbox", attempt=key, rel_path=rel,
                                   meta_rel_path=meta_rel)
                continue
            if self._stop_requested():
                return "stopped"
            text = outbox_path.read_text(encoding="utf-8")
            meta_text = meta_path.read_text(encoding="utf-8")
            findings = scan_receipt(text)
            if findings:
                self.ledger.append("attempt_quarantined", attempt=key,
                                   findings=[f.as_dict() for f in findings][:20],
                                   reason="rescan_before_upload")
                continue
            self.out("[补传] %s" % rel)
            self._upload(key, rel, text, meta_text, meta_rel, self._entry_for(key))
            if self._stop_requested():
                return "stopped"
        return "wait"

    def _entry_for(self, key: str):
        task_id, _, rev = key.partition("@r")
        return TaskEntry(task_id=task_id, revision=int(rev or 1), status="published",
                         task_path="", task_commit="", content_sha256="", scopes=(), title="")

    # ------------------------------------------------------------ 恢复

    # 只有这些事件代表「尝试已经开始但尚未收敛」；其他事件（如 task_not_trusted）不参与恢复判定。
    IN_FLIGHT_EVENTS = ("claim", "attempt_start", "attempt_phase", "child_started",
                        "attempt_harness_exit")

    def _sweep_decision(self, key: str, slot: dict) -> str | None:
        """判断未收敛尝试的归属：abort（未执行）/ recovery（结果不明）/ None（交给补传或无需处理）。"""
        last = slot["last"]
        if last in TERMINAL or last in NEEDS_REVIEW or last in RESUMABLE_UPLOAD:
            return None
        if last not in self.IN_FLIGHT_EVENTS:
            return None
        phase = None
        for record in reversed(self.ledger.records):
            if record.get("attempt") == key and record.get("event") == "attempt_phase":
                phase = record.get("phase")
                break
        if last == "claim" or (last == "attempt_phase" and phase == "accepted"):
            return "abort"
        if last == "attempt_phase" and phase in ("result_saved",):
            return None
        if last == "attempt_phase" and phase == "uploading":
            return None
        return "recovery"

    def _recovery_sweep(self) -> None:
        for key, slot in sorted(self.ledger.attempts().items()):
            decision = self._sweep_decision(key, slot)
            if decision == "abort":
                self.ledger.append("attempt_aborted_before_execution", attempt=key,
                                   reason="worker_crashed_before_spawn",
                                   note="未开始执行，结果可确定为无；不重跑")
                self.out("[恢复] %s 在执行前中断，标记 failed（不重跑）。" % key)
            elif decision == "recovery":
                self.ledger.append("attempt_recovery_required", attempt=key,
                                   reason="worker_crashed_mid_attempt",
                                   note="结果不明，禁止自动重跑；需人工 ack")
                self.out("[恢复] %s 上次未收敛，标记 recovery_required。" % key)

    # ------------------------------------------------------------ 停止 / 心跳

    def _stop_reason(self) -> str:
        if self.cfg.stop_path.exists():
            return "本机 STOP 文件"
        if self._pause_seen_at:
            return "仓库暂停标志"
        return "停止请求"

    def _stop_requested(self) -> bool:
        if self.cfg.stop_path.exists():
            return True
        return self._pause_seen_at is not None

    def _heartbeat(self, phase: str) -> None:
        payload = {
            "pid": os.getpid(),
            "ts": now_iso(),
            "epoch": time.time(),
            "phase": phase,
            "mode": self.mode,
            "child_pid": self._child_pid,
        }
        try:
            atomic_write_text(self.cfg.heartbeat_path, json.dumps(payload, ensure_ascii=False))
        except OSError:
            pass

    def _on_child(self, pid: int) -> None:
        self._child_pid = pid
        self.ledger.append("child_started", pid=pid)

    def _write_worker_state(self, phase: str) -> None:
        payload = {
            "pid": os.getpid(),
            "mode": self.mode,
            "phase": phase,
            "ts": now_iso(),
            "branch": self.cfg.repo_branch,
            "product": self._product_summary() if self.mode == "live" else None,
        }
        try:
            atomic_write_text(self.cfg.worker_state_path,
                              json.dumps(payload, ensure_ascii=False, indent=2))
        except OSError:
            pass

    def _product_summary(self) -> dict:
        if not self.product:
            return {}
        return {
            "version": self.product.get("version"),
            "help_ok": self.product.get("help_ok"),
            "version_allowed": self.product.get("version_allowed"),
            "ok": self.product.get("ok"),
            "errors": self.product.get("errors", [])[:5],
        }

    def _record_once(self, event: str, dedupe: str, **fields) -> None:
        for record in reversed(self.ledger.records):
            if record.get("event") == event and record.get("dedupe") == dedupe:
                return
            if record.get("event") == event:
                break
        payload = dict(fields)
        payload["dedupe"] = dedupe
        self.ledger.append(event, **payload)

    def _sleep(self, seconds: float) -> None:
        deadline = time.time() + max(0.0, seconds)
        while time.time() < deadline:
            if self.cfg.stop_path.exists():
                return
            time.sleep(min(0.25, max(0.05, deadline - time.time())))
