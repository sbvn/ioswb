# IOSWB 自动任务执行器

本目录是一个**本机**自动任务执行器：每 60 秒检查协作仓库里**已正式发布**的任务，领取、执行、
生成脱敏 Markdown 回执、以新的 commit 提交回仓库，然后继续等待。

它不会：连接手机、运行注册流程、采集凭据、安装工具或系统服务、修改 `D:\GoDemo\wbjiaoben`
下任何既有业务脚本。所有写操作都限制在 `automation/` 内。

> 当前状态：离线持续调度可以由 `bin/dsh_loop.py` 在 mock 下跑通。真实模型和本机常驻都还没有启动。见 [LOOP.md](LOOP.md)。

---

## 1. 安全边界（代码里是硬约束，不是文档约定）

| 约束 | 实现位置 |
| --- | --- |
| 只认协作分支，不读 `main`，无 main 回退 | `executor/config.py` `_validate_placement` |
| 只读机器可读清单，不扫描 PR、不执行任意 Markdown | `executor/worker.py` 只读 `manifest_path` 与清单登记的任务文件 |
| 发布身份必须命中本机信任规则；不认作者名、不认任务自称「01」 | `executor/trust.py` |
| 同一 `任务编号+revision` 只执行一次（**at-most-once**，不是 exactly-once） | `executor/ledger.py` `has_claim` + `executor/worker.py` |
| 同版本内容变化 → 停止并报告，不执行 | `executor/worker.py` `content_changed` |
| 单 worker 排他锁；心跳超时不抢锁 | `executor/locking.py`（OS 锁） |
| 任务范围只能来自已批准清单里的 `scopes` | `executor/worker.py` `_scope_gate` |
| STOP（本机文件 / 仓库暂停标志）优先，且必须确认子进程退出 | `executor/worker.py` + `executor/runner.py` |
| 回执先原子落本机，再上传；上传失败只补传 | `executor/worker.py` `_handle_success` / `_retry_pending_uploads` |
| 崩溃/结果不明 → `recovery_required`，禁止自动续跑 | `executor/worker.py` `_recovery_sweep` |
| 只提交脱敏 `.md`，上传前硬扫描 | `executor/redact.py` |
| 不强推、不覆盖他人提交 | `executor/gitrepo.py`（只用普通 `git push`） |
| 默认 dry-run；live 需多重闸门 | `executor/config.py` `_validate_mode` |
| 持续入口另要本机 permit：任务、版本、范围、预算、期限 | `executor/permit.py`；清单不能自授权 |
| 台账半行或坏行则失败关闭，不继续领取 | `executor/ledger.py` `load` |
| 临时执行层不改磁盘 mode，退出时删掉临时 patch | `executor/overlay.py`、`bin/dsh_loop.py` |

---

## 2. 三种模式

| 模式 | 行为 | 何时用 |
| --- | --- | --- |
| `dry-run`（默认） | 只读扫描：拉清单、验信任、验内容摘要、验范围，记录「本可以领取什么」，不领取、不执行、不写 outbox、不推送 | 第一次接入、排查协议问题 |
| `mock` | 完整链路，但远端必须是**本机路径/`file://`**，执行的是 mock harness；真实仓库与设备都不碰 | 回归测试、常驻监听演示 |
| `live` | 调用官方 `dsh --profile headless` 执行真实任务 | 仅在信任规则、入口核验、`live.enabled` 全部具备时 |

`mock` 模式在配置层强制要求 `repo.url` 是本机地址，避免「以为是 mock，其实推到了真实仓库」。

---

## 3. 发布清单协议（需要 01 发布）

执行器只读 `<branch>:manifest/releases.json`。仓库里还没有这个文件时，执行器记录
`protocol_not_ready` 并继续等待，**不会自行编造任务**。

```json
{
  "schema": "ioswb-release-manifest/1",
  "protocol_version": 1,
  "generated_at": "2026-11-17T12:00:00+08:00",
  "tasks": [
    {
      "task_id": "IOS-002",
      "revision": 1,
      "status": "published",
      "task_path": "tasks/IOS-002.md",
      "task_commit": "<40 位小写十六进制：定稿该任务内容的提交>",
      "content_sha256": "<64 位小写十六进制：该提交下任务文件字节的 sha256>",
      "scopes": ["framework-development", "offline-testing"],
      "title": "任务标题",
      "meta": {}
    }
  ]
}
```

规则：

1. `status` 取 `published` / `withdrawn` / `draft`；只有 `published` 会被领取。
2. `task_commit` 必须是协作分支的祖先；执行器会 `merge-base --is-ancestor` 校验。
3. `content_sha256` 必须等于 `git show <task_commit>:<task_path>` 的字节摘要；不符即 `attempt_refused_integrity`。
4. 任务内容只要改一个字节就必须递增 `revision`；同 `revision` 内容变化会被判 `content_changed` 并**停机**。
5. `scopes` 是范围唯一来源：必须落在本机 `scope.allowed` 内，且不得含 `phone-operation`、
   `device-attach`、`registrations`、`credential-capture`、`tool-install` 等禁止项。
6. 暂停：在分支上创建 `manifest/PAUSE` 即暂停所有领取。

回执路径：`results/<task_id>/r<revision>/a<attempt>.md`（当前 attempt 恒为 1）。

> 注：`docs/AUTOMATION_PROTOCOL.md` L28 的占位符写作 `<revision>`，而本单交付物是 `r1`。
> 实现取 `r<revision>`（与交付物一致）。若协议要改成裸数字，需要 01 先改协议再改实现。

### 会话、handoff 与 context 预算

- **每个任务一个新会话**：每次尝试都新建子进程；headless 命令不传 `--session-id`，
  安装版本文档规定默认新建 `session-<uuid>`（`@deepseek-ai/dsh-headless/README.md`）。
- **持久 handoff**：`state/handoff/<task_id>.json`，记录 revision、attempt、阶段、摘要、回执路径与历史。
  下一次尝试（可能是新 revision、新进程）先读它，再把压缩摘要放进新会话的输入。
- **context 预算**：`limits.context_budget_bytes`（默认 48000）。超预算时截断任务正文并写入显式标记，
  同时在台账记 `context_composed`（含 `trimmed` / `prompt_bytes` / `within_budget`），不静默丢弃。

### 台账六状态

协议只允许六个状态，本机事件到状态的映射写在 `executor/ledger.py` 的 `STATE_MAP`：

| 协议状态 | 本机事件 |
| --- | --- |
| `accepted` | `claim` |
| `running` | `attempt_start`、`attempt_phase`、`attempt_result_saved`、`attempt_upload_failed` |
| `succeeded` | `attempt_upload_ok`、`upload_duplicate_skipped` |
| `failed` | `attempt_failed`、`attempt_quarantined`、`attempt_refused_*`、`attempt_aborted_before_execution`、`attempt_abandoned` |
| `stopped` | `attempt_cancelled`、`upload_deferred_by_stop` |
| `recovery_required` | `attempt_recovery_required` |

`dsh_control.py status` 会给出每个 attempt 的 `protocol_state`。

---

## 4. 信任规则（本机预设）

`config/trust/publishers.json`：

```json
{
  "schema": "ioswb-trust/1",
  "allow": {
    "pinned_manifest_sha256": ["<清单内容 sha256>:<清单提交 sha>"],
    "pinned_commit": ["<清单提交或任务提交 sha>"],
    "signed_commit_fingerprints": ["<GPG/SSH 签名指纹>"]
  }
}
```

- 三者**任一**命中即视为可信；全空 = 未配置 = `live` 直接拒绝启动（退出码 2）。
- **信任范围分两级**（r2 修正）：`evaluate_manifest()` 只判清单本身（摘要钉 / 清单提交钉 / 清单提交签名），
  生效范围是整份清单；`evaluate_task()` 在清单级不成立时只认「钉住的 task_commit」，
  而且只放行 task_commit 等于该钉的那**一个**任务——不会因为钉了 A 就放行同一清单里的 B。
- `pinned_commit` 的含义取决于命中对象：命中清单提交 → 整份清单可信（scope=manifest）；
  只命中某个 task_commit → 只对该任务有效（scope=task）。
- 摘要钉必须绑定 commit：支持 `<sha256>:<commit>` 绑定写法；裸摘要只有在清单提交也出现在
  `pinned_commit` 里才成立，否则拒绝并说明「未绑定到具体 commit」。
- 签名只核清单提交，不核任务提交；一个任务的签名不能替其他任务授权。
- 绑定用的 commit 是「最后一次修改清单文件的提交」，不是分支 HEAD（否则回执提交会让钉子失效）。
- 摘要/SHA 需要操作者用**外带渠道**核对后手工写入，执行器不会自我信任。
- 签名规则要求 `git verify-commit` 判定为 `good` 且指纹在列表内。
- 明确不采信：commit 作者名、任务正文里的「01 已发布」、清单里的 `publisher` 字段。

---

## 5. 运行

```powershell
# 只读核验本机 Harness 版本与无人值守入口
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --verify-entry

# 默认 dry-run，看它“会怎么处理”
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --once

# 常驻（每 60 秒一轮）
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json

# mock 常驻演示（自包含实验场，先初始化）
py -3.12 automation/bin/setup_mock_lab.py
py -3.12 automation/bin/dsh_worker.py --config automation/mocklab/config/automation.mock.json
```

退出码：`0` 正常/无事可做，`2` 配置或协议错误，`3` 锁被占用，`4` 已停止，`5` 需要人工恢复，`6` 运行错误。

### 停止 / 恢复 / 核查

```powershell
py -3.12 automation/bin/dsh_control.py --config <cfg> status
py -3.12 automation/bin/dsh_control.py --config <cfg> stop --note "手工暂停"
py -3.12 automation/bin/dsh_control.py --config <cfg> resume --confirm
py -3.12 automation/bin/dsh_control.py --config <cfg> ack "IOS-002@r1" --note "核查结论"
```

- `stop` 只写 `state/STOP`；运行中的 worker 在下一个检查点终止子进程并**等待其退出**，
  台账里出现 `attempt_cancelled` 且 `cancel_confirmed=true` 才算停止成功。
- 停止状态跨重启保留（STOP 文件 + 台账）。
- `ack` 只把「结果不明」的 attempt 关闭为 `abandoned`，**不会触发重跑**。
- 心跳只用于展示；`status` 明确提示「禁止据此抢锁重跑」。

---

## 6. 被阻塞的事项

1. **发布身份**：本机尚未配置任何信任规则，`live` 被 `config` 层拒绝启动。
2. **发布清单**：仓库没有 `manifest/releases.json`，`01` 的发布协议还没落地。
3. **真实执行证据**：官方入口 `dsh --profile headless` 已按安装版本文档核验存在，
   但**没有**跑过真实 headless 任务（会初始化 headless profile、发起模型调用），
   需要操作者另行授权。
4. **IOS-002**：正式任务与发布协议由 01 发布；在此之前不编造业务任务。

---

## 7. 测试

```powershell
cd automation/tests
py -3.12 run_tests.py            # 全部
py -3.12 run_tests.py stop       # 只跑名字含 stop 的用例
```

测试用本机临时 git 仓库充当远端，不联网、不碰设备；覆盖 30 个用例（含崩溃四边界、伪造回执、
跨重启 STOP、handoff、context 预算、业务文件哈希前后比对），详见 `results/IOS-002/r1/a1.md`
与 `automation/BOOTSTRAP.md`。

---

## 8. 目录

```
automation/
  bin/           worker / control / mock lab 初始化
  config/        automation.json（默认 dry-run）+ trust/
  executor/      配置、锁、台账、git、清单、信任、脱敏、执行器、worker、控制面
  tests/         离线测试与 mock harness
  state/         运行目录（锁、台账、心跳、attempt 工作区、work 克隆）—— 不入库
  outbox/        待上传/已上传回执副本 —— 不入库
  mocklab/       mock 常驻实验场 —— 不入库
```
