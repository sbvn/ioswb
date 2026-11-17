# 分级自动派发协议

- 状态：01 发布稿，待提交到分支 `cursor/init-collab-docs-2e45` 后生效
- 发布人：01 研发总管
- 日期（Asia/Hong_Kong）：2026-11-17
- 决策依据：用户 2026-11-17 16:47 明确拍板「低风险任务自动跑，碰手机的仍一次一单」
- 仓库：https://github.com/sbvn/ioswb
- 适用 ref：`cursor/init-collab-docs-2e45`（与 AUTOMATION_PROTOCOL 一致，不读 main）
- 本文件是 AUTOMATION_PROTOCOL 的增补。两者冲突时，以更严的一边为准。

## 一句话

等待器可以常驻并自动执行**自动档**任务；**人工档**任务永远不自动执行，
仍按 SMOKE-001 r2 的方式一次一单、用户在场交接（RUN-ONCE）。

## 分档

### 自动档（同时满足全部条件才可自动领取）

1. 清单 `manifest/releases.json` 中 `status=published`，且清单提交的 SSH 签名
   能用本机已钉住的发布公钥验过（指纹
   `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`，身份 `cursoragent@cursor.com`）。
   未签名、签名 bad、换公钥：一律 0 执行（AUTO-CONNECT-001 r2 已独立复跑证明）。
2. `task_commit` 是适用 ref 的祖先，且 `content_sha256` 等于
   `git show <task_commit>:<task_path>` 的原始字节 sha256。同 revision 内容变化即阻断。
3. `scopes` 全部落在本机 `scope.allowed` 内。当前只允许两个：
   `framework-development`、`offline-testing`。
4. 写入范围只限业务目录内的 `automation/`（框架、离线测试、状态）与仓库的
   `results/` 回执路径。不改 `automation/` 以外的任何业务脚本。
5. 不连接手机、不连接 Frida、不启动任何 App、不做真实触摸、不安装工具或服务、
   不改系统配置、不涉及注册与凭据。
6. 单 worker、单任务串行（等待器每轮最多派发一个），每个 revision 最多尝试一次，
   台账 at-most-once；结果不明进 `recovery_required`，不自动重跑。

### 人工档（满足任一即归人工档，永不自动）

- scope 含 `phone-operation`、`device-attach`、`registrations`、
  `credential-capture`、`tool-install` 等禁止项——执行器代码里恒拒绝
  （`test_scope_denied_refused` 已证明），清单里写了也不会被领取，更不会排队等待。
- 需要改 `automation/` 以外的业务脚本。
- 需要启动 App、真实触摸、spawn、kill、安装工具、改服务或系统配置。
- 任务单里写明「人工档」或附带 RUN-ONCE 交接文件的。

人工档的执行方式不变：01 另发 RUN-ONCE 交接，用户在场，本机现有 Harness
会话读一次、跑一次、跑完恢复 `mode=dry-run` 并回执。

## 为什么不需要新代码

以下能力已在现有执行器里实现并经离线/独立复跑验证，本协议只是把开关打开：

| 能力 | 位置 / 证据 |
| --- | --- |
| 等待器派发开关 | `connect_wait.py`：带 `--dispatch` 且 mode 不是 dry-run 时才调用 Worker，每轮最多一个 |
| scope 门禁 | `executor/worker.py` `_scope_gate`：禁止 scope 恒拒；allowed 之外拒 |
| 签名门禁 | AUTO-CONNECT-001 r2：未签名 0 执行、改清单签名 bad、换公钥被拒 |
| 成功判定 | `abd5726` 收紧：exit 0 且恰一条 final 且 `final.reason.kind` 严格等于 `completed` 且回执非空 |
| 防重复 | 台账 claim + 操作系统排他锁；同 revision 只领一次 |
| 回执可靠 | 先本机 spool 原子落盘再上传；上传失败只补传，不重跑 |
| 急停 | 本机 STOP（跨重启有效）、仓库 `manifest/PAUSE`、改回 `mode=dry-run`，三者任一生效 |

## 常驻开启后的常态

- 本机配置：`mode=live`、`live.enabled=true`、`live.reason` 清空、
  `harness.unattended.enabled=true`，超时保持 3600/3600（框架任务上限 60 分钟）。
- 等待器以 `--dispatch` 常驻；进程退出后下次启动第一条记录必须写明
  「上次已退出，之前不是常驻」，不得声称一直在跑。
- 01 发布自动档任务的固定顺序：先提交任务文件 → 用该提交计算
  `content_sha256` → 更新清单（`task_commit` 指向任务提交）→ 提交清单
  （必须由发布通道签名）→ 更新 TASKS.md 索引。不再需要逐份清单做外带钉住，
  因为签名门禁覆盖后续清单；但任务身份双值（blob SHA-1 与 content_sha256）
  仍分开记录，不得互相替代。
- 手机、Frida、真实触摸、注册、凭据采集仍未授权。本协议不改变这一点。

## 急停与回滚

任一情况出现，立即回滚到 dry-run 并停止等待器、写回执说明：

- 出现非自动档任务被领取或执行的迹象；
- 签名验不过但仍被领取；
- 同一 revision 被执行第二次；
- 回执内容与任务要求不一致却被判成功；
- 用户口头或书面要求停止。

回滚动作只有三步：停等待器进程 → `mode=dry-run`、`live.enabled=false`、
`harness.unattended.enabled=false` → 在回执/验收里记录原因。回滚不删台账、
不清 claim、不覆盖已有回执。

## 首次试跑

用 SMOKE-002 做无人值守试跑（见 `tasks/IOS-AUTO-SMOKE-002.md`）：
发布后**不给 Harness 发任何消息**，等待器应在一个轮询周期量级内自行领取、
执行并回传 `results/SMOKE-002/r1/a1.md`。15 分钟未领取即判试跑失败，
按上面回滚，不得用人工交接补跑冒充自动成功。
