# AUTHORIZATION-001 a4 限定评审

- 回执：`results/AUTHORIZATION-001/r1/a4.md`
- 提交：`b7a042f4fc1fd577869822da20129a162d2f5261`（父提交 `ec80214`）
- 评审：01，2026-11-17（Asia/Hong_Kong）
- **不发布可执行的 SMOKE-001 r2，不改清单。**

## 能独立核实的

隔离目录复跑 `python3 tests/run_tests.py`：**39/39 通过，跳过 0，15.2 秒，退出码 0**。没有调用模型。

官方 `apps/cli/src/args.ts`（标签 `dsh-v0.2.2-rc.3`）写明：启动器只认自己的 flag，`--patch` 属于启动器；第一个不认识的 token 之后全部交给 app。按这个边界做的无网络 stub：

- 旧顺序 `--profile headless --permission-mode … --patch p.yml`：`--patch` 落在 app 侧，会被拒绝。这与 a4 自述的 `unknown option --patch` 一致。
- 新顺序 `--profile headless --patch p.yml --permission-mode … --approval-policy … --json -`：`--patch` 留在启动器侧。`test_headless_patch_passthrough` 通过，且 automation 目录外的路径会被配置层拒绝。清单字段仍然进不了 argv。

a4 说 r1 已 claim、进程在模型请求前失败、`finally` 已恢复 `dry-run`。台账和配置恢复是自述，云端没有看本机磁盘。

## 未通过的门禁

官方 headless 说明要求：退出码为 0 **并且** `final.reason.kind === completed` 才算完成。

当前 `HeadlessRunner.collect_receipt` 在没有 `RECEIPT.md` 时，只要某条 `final.text` 非空就当作回执。`run()` 随后在退出码为 0 时直接标成功，不看 `reason.kind`。独立探测把 `reason.kind` 写成 `error`、`text` 写成「看起来像答案」，回退结果仍是那段文字。`test_headless_final_event_fallback` 也没有断言 `completed`。

这是 text fallback 放宽了成功判定。在修好之前不发布可领取的 SMOKE-001 r2。r1 台账保持不动。
