# BOOTSTRAP 回执：GitHub 自动任务执行器（离线框架）

- 回执版本：v1.0
- 生成时间（Asia/Hong_Kong）：2026-11-17 12:57
- 执行方：用户本机 DeepSeek Harness（自述：DeepSeek Harness 桌面版，profile `desktop`，产品包 `@deepseek-ai/dsh` **0.2.2-rc.3**）
- 业务目录：`D:\GoDemo\wbjiaoben`
- 协作仓库 / 分支：`https://github.com/sbvn/ioswb` / `cursor/init-collab-docs-2e45`（不读 main）
- 新增目录：`D:\GoDemo\wbjiaoben\automation\`
- 未改动：`weibo_browse.py`、`weibo_browse_agent.js`、`weibo_touch_agent.js`、`weibo_batch.py`、`weibo_min_agent.js`、`weibo_stability_probe.py`、`README.md`、`AGENTS.md` 以及 `runs*/` 全部既有产物
- 未连接手机、未运行注册流程、未安装系统服务、未安装任何工具或插件

> 结论先写清楚：**离线框架完成，19/19 mock 用例通过，mock 模式已可常驻；真实自动闭环未完成，
> live 被双重阻塞（信任规则未配置 + 发布清单协议未发布）。** 不得把本回执读成「真实自动执行已跑通」。

---

## 1. 变更文件

全部新增，无删除、无修改既有文件。

| 文件（相对 `automation/`） | 行数 | 作用 |
| --- | ---: | --- |
| `README.md` | 109 | 操作手册：边界、模式、清单协议、启动/停止、测试 |
| `.gitignore` | 7 | `state/`、`outbox/`、`mocklab/`、`tests/.work/` 不入库 |
| `config/automation.json` | 51 | 默认配置：`mode=dry-run`、`live.enabled=false`、绑定协作分支 |
| `config/automation.example.json` | 51 | 同结构模板 |
| `config/trust/publishers.json` | 9 | 信任规则：**allow 全空 = 未配置**（这是 live 被拒的直接原因） |
| `config/trust/publishers.example.json` | 15 | 信任规则模板 |
| `executor/common.py` | 116 | 常量、sha256、原子写、JSONL 追加、路径校验 |
| `executor/config.py` | 239 | 配置加载、运行目录归位、模式闸门（dry-run/mock/live） |
| `executor/locking.py` | 60 | **OS 排他锁**（Windows `msvcrt.locking` / POSIX `flock`） |
| `executor/ledger.py` | 139 | 持久化台账（append-only JSONL + fsync）、attempt 派生状态 |
| `executor/gitrepo.py` | 134 | clone/fetch/read/commit/push；**普通 push，不含 force**；凭据只做脱敏 |
| `executor/manifest.py` | 123 | 机器可读发布清单解析、严格校验、内容摘要与祖先链绑定 |
| `executor/trust.py` | 99 | 信任规则核验（摘要钉 / 提交钉 / 签名指纹），不认作者名 |
| `executor/redact.py` | 51 | 回执脱敏硬扫描（UDID、手机号、私钥、令牌、个人路径、base64 大块） |
| `executor/runner.py` | 282 | 执行适配器：mock / `dsh --profile headless`；取消与等待退出；产品核验 |
| `executor/worker.py` | 439 | 单 worker / 单任务状态机（领取→执行→回执→上传→等待） |
| `executor/control.py` | 93 | status / stop / resume / ack |
| `executor/__init__.py` | 9 | 包说明 |
| `bin/dsh_worker.py` | 48 | worker 入口（含 `--verify-entry`） |
| `bin/dsh_control.py` | 44 | 操作员控制台 |
| `bin/setup_mock_lab.py` | 142 | 自包含 mock 实验场初始化 |
| `tests/lab.py` | 258 | 测试实验台（本机 git 仓库充当远端） |
| `tests/run_tests.py` | 296 | 19 个离线用例 |
| `tests/fake_harness.py` | 80 | mock harness（真子进程，可被取消，父进程死则退出） |

运行产物（不入库）：`automation/state/`（锁、台账、心跳、attempt 工作区、work 克隆）、
`automation/outbox/`、`automation/tests/.work/`、`automation/mocklab/`。

---

## 2. 真实调用入口：核实结果与文档依据

### 2.1 本机 Harness 产品版本（已核实，不是猜测）

| 项 | 值 | 核实方式 |
| --- | --- | --- |
| 产品包 | `@deepseek-ai/dsh` | 读 asar 内 `package.json`（`ELECTRON_RUN_AS_NODE=1` + `DSH_NODE_EXECUTABLE`） |
| 版本 | **0.2.2-rc.3** | 同上；并用 `dsh --version` 交叉验证，exit 0，输出 `0.2.2-rc.3` |
| 安装锚点 | `DSH_INSTALL_DIR` → `...\app.asar\dsh\node_modules\@deepseek-ai\dsh` | 环境变量 + 文件读取 |
| 启动器 | `lib/bin.js`（`bin: {"dsh": "lib/bin.js"}`） | package.json |
| engines | `node >= 24.9.0`（本机 Electron 运行时 24.21.0） | package.json / `desktop-runtime.json` |

上一份 IOS-001 回执里「产品版本未能取得」，本次通过 asar 内读取 + `dsh --version` 补上了。

### 2.2 官方文档支持的无人值守调用方式（已核实存在）

依据来自**本机安装版本内附带的文档**（`@deepseek-ai/dsh` 的 `docs/` 与各包 `README.md`）：

1. `@deepseek-ai/dsh/README.md`「Entry modes」：
   `dsh --profile headless "job"` —— *Run one fresh persisted session, print the final answer, and exit.*
2. `@deepseek-ai/dsh-headless/README.md`「Running a one-shot task」：
   `dsh --profile headless "run the tests"`；任务来自位置参数，省略或用 `-` 时来自 stdin。
3. 同文档「Supervising implementation tasks」给出监督者模式：
   `dsh headless --permission-mode workspace-write --add-dir "$git_dir" --json - < task.txt > run.jsonl`
4. 同文档「Machine-readable output」：`--json` 输出 NDJSON（`session` 开头、`final` 结尾）。
5. 同文档「Exit mapping」：完成 `turn/end` 退出 0，其余退出 1；并要求
   *both process exit zero and `final.reason.kind === 'completed'`* 才算完成。
6. 同文档明确：「A supervisor that interrupts a process must await its exit before resuming its
   Session.」——这正是本执行器 STOP 语义（终止后必须 `wait()` 确认退出）的文档依据。
7. `dsh --help` 实测（exit 0）在 Examples 里列出 `dsh headless "run the tests"`。

### 2.3 已执行 vs 未执行的核验动作

| 动作 | 是否执行 | 结果 |
| --- | --- | --- |
| 读 asar 内 `package.json` 取版本 | 已执行 | `0.2.2-rc.3` |
| `dsh --version` | 已执行 | exit 0，`0.2.2-rc.3` |
| `dsh --help` | 已执行 | exit 0，含 headless 示例 |
| 读 `dsh-headless` / `dsh` 的 README 文档 | 已执行（只读） | 见 2.2 |
| **`dsh --profile headless "<task>"` 实跑** | **未执行** | 会初始化 `headless` profile 并触发模型调用，属未授权动作 |
| `dsh headless --json` 实跑 | **未执行** | 同上 |
| 连接设备 / 附加 App / 触摸 / spawn / kill | **未执行** | 任务禁止 |

因此入口判定的准确表述是：**入口在文档与启动器层面已核实存在，端到端实跑未验证。**

---

## 3. 测试结果

```text
cd automation/tests
py -3.12 run_tests.py
```

结果：**19 / 19 通过**，用时约 42 s。全部为离线 mock（本机临时 git 仓库充当远端），
未连接手机、未访问网络、未使用真实仓库。

| # | 用例 | 验证点 |
| ---: | --- | --- |
| 1 | `test_new_task_executes_once_and_uploads` | 新任务只执行一次，回执按 `results/<task>/r<rev>/a1.md` 上传 |
| 2 | `test_rescan_does_not_rerun` | 重复扫描不重跑、不产生新提交 |
| 3 | `test_dry_run_has_no_side_effects` | 默认 dry-run 不领取、不执行、不写 outbox、不推送 |
| 4 | `test_untrusted_manifest_refused` | 信任规则未配置 → 拒绝执行 |
| 5 | `test_forged_task_digest_refused` | 清单摘要与任务内容不符 → 拒绝（伪造任务被挡） |
| 6 | `test_scope_denied_refused` | 越界 scopes（`phone-operation`）→ 拒绝 |
| 7 | `test_content_change_stops_without_rerun` | 同编号同版本内容变化 → 停机报告，不重跑 |
| 8 | `test_upload_failure_then_reupload_only` | 推送失败（远端拒绝）→ 回执留在本机；恢复后**只补传**，执行次数仍为 1 |
| 9 | `test_stop_before_claim` | STOP 时点一：不领取，且停止状态跨重启保留 |
| 10 | `test_stop_during_execution_cancels_and_confirms_exit` | STOP 时点二：终止子进程并记录 `cancel_confirmed=true`；无回执产出 |
| 11 | `test_stop_after_result_defers_upload_then_resume_uploads` | STOP 时点三：回执已原子落盘但不上传；resume 后只补传 |
| 12 | `test_crash_recovery_requires_ack` | 杀进程模拟崩溃 → `recovery_required`、退出 5、不自动重跑；ack 后仍不重跑 |
| 13 | `test_second_worker_cannot_take_lock` | 第二个 worker 拿不到 OS 锁（退出 3），不出现第二次执行 |
| 14 | `test_redaction_quarantines_receipt` | 回执含 UDID/手机号/个人路径 → 隔离，不入 outbox、不上传 |
| 15 | `test_protocol_not_ready_waits` | 无清单 → 记录 `protocol_not_ready` 并等待，不编造任务 |
| 16 | `test_repo_pause_flag_stops` | 仓库 `manifest/PAUSE` → 退出 4，不执行 |
| 17 | `test_live_blocked_without_trust_rules` | live + 无信任规则 → 配置错误退出 2，不执行 |
| 18 | `test_control_status_reports_state` | status 正确报告锁、STOP、attempt 状态、心跳；含「禁止据此抢锁」提示 |
| 19 | `test_business_files_untouched` | 既有业务脚本仍在、未被删除 |

---

## 4. 设计要点与不变量

1. **单 worker / 单任务**：`state/worker.lock` 用操作系统排他锁；第二个进程直接退出 3。
   心跳只做展示，`status` 明确写「禁止据此抢锁重跑」；锁只由 OS 在进程消失时释放。
2. **只执行一次**：台账 `claim` 记录一旦出现，同 `(task_id, revision)` 永不执行第二次；
   取消、超时、崩溃都**消耗**该版本，要继续必须由团队发新 revision。
3. **内容漂移即停**：清单里同 `revision` 的 `content_sha256` 与领取时不同 → `content_changed`，
   停机报告，不执行。
4. **信任只认本机预设**：清单摘要钉 / 提交钉 / 签名指纹，三者任一命中；
   **不认 commit 作者名，不认任务正文自称「01」**。未配置 → live 直接拒绝启动。
5. **STOP 三处检查**：领取前、执行中（0.2 s 轮询）、回执已存未上传；取消后
   `proc.terminate()` → 宽限 → `proc.kill()` → `wait()` 确认退出，台账记 `cancel_confirmed`。
6. **先落盘再上传**：回执用「同目录临时文件 + fsync + `os.replace`」原子写入 `outbox/`，
   然后才提交到 `results/<task>/r<rev>/a1.md`。上传失败只重传；崩溃后结果不明 → `recovery_required`。
7. **脱敏闸门**：上传前对**即将入库的那份字节**扫描，命中即隔离（`state/quarantine/`），
   不入 outbox、不入库。
8. **Git 纪律**：只用普通 `git push`（无 `--force*`）；先 fetch 再在最新头重建提交，避免覆盖他人提交；
   凭据由本机 credential helper 处理，代码从不读取/打印；错误信息对 URL userinfo 做脱敏。
9. **范围闸门**：硬闸门只看清单 `scopes`（且必须在 `scope.allowed` 内、不得含禁止项）；
   任务正文的关键词扫描只记 `scope_text_warning`，不用于否决——正文写「不注册」不应导致拒跑，
   授权来源是可信清单而不是词法。
10. **默认 dry-run**：配置默认 `mode=dry-run`；`live` 需要 `live.enabled` + `harness.unattended.enabled`
    + 版本白名单 + 非空信任规则同时成立，否则加载配置即 fail-closed。

---

## 5. 启动 / 停止命令

```powershell
# --- 只读核验本机 Harness 与无人值守入口（不启动 profile、不调用模型）
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --verify-entry

# --- 默认 dry-run：看它“会怎么处理”，不产生任何副作用
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --once

# --- 正式配置常驻（当前仍是 dry-run，且协议未就绪时会记录 protocol_not_ready 后等待）
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json

# --- mock 常驻演示（自包含实验场，只动 automation/mocklab/）
py -3.12 automation/bin/setup_mock_lab.py
py -3.12 automation/bin/dsh_worker.py --config automation/mocklab/config/automation.mock.json

# --- 停止 / 恢复 / 核查 / 状态
py -3.12 automation/bin/dsh_control.py --config <cfg> stop --note "手工暂停"
py -3.12 automation/bin/dsh_control.py --config <cfg> resume --confirm
py -3.12 automation/bin/dsh_control.py --config <cfg> ack "IOS-002@r1" --note "核查结论"
py -3.12 automation/bin/dsh_control.py --config <cfg> status
```

退出码：`0` 正常/无事可做，`2` 配置或协议错误，`3` 锁被占用，`4` 已停止，`5` 需要人工恢复，`6` 运行错误。

---

## 6. 是否正在常驻

**是，但只有 mock 模式在常驻；真实模式没有常驻。**

| 项 | 值 |
| --- | --- |
| 进程 | `python.exe … automation/bin/dsh_worker.py --config automation/mocklab/config/automation.mock.json` |
| 启动方式 | 本次会话管理的后台任务（**不是** Windows 服务、不是计划任务、未写注册表） |
| 模式 | `mock`，远端 = `automation/mocklab/remote`（本机 git 仓库） |
| 轮询间隔 | 60 s |
| 已处理 | `MOCK-900@r1`：领取 → 执行 1 次 → 回执原子落盘 → 推送成功（`attempt_upload_ok`） |
| 台账 | `automation/mocklab/state/ledger.jsonl`（10 条记录，0 条待核查） |
| 回执 | `automation/mocklab/remote` 分支 `results/MOCK-900/r1/a1.md` |
| 锁 | 持有中（`status.lock_held=true`），因此不会出现第二个 worker |
| 会话结束后 | 该后台任务随会话结束可能被回收；重启方式见第 5 节，状态（台账/STOP）在磁盘上保留 |

未启动 `automation/config/automation.json`（正式配置）的常驻：它现在只会每 60 秒记录一次
`protocol_not_ready`，没有收益，且容易让人误以为「真实自动执行已在跑」。

---

## 7. 仍被阻塞的事项

| # | 阻塞项 | 阻塞原因 | 解除条件 |
| ---: | --- | --- | --- |
| 1 | **真实执行（live）** | 本机信任规则 `allow` 为空 | 操作者用外带渠道核对清单后，把清单摘要 / 提交 SHA / 签名指纹写入 `config/trust/publishers.json` |
| 2 | **任务来源** | 仓库分支上没有 `manifest/releases.json` | 01 按 README 第 3 节的协议发布清单 |
| 3 | **IOS-002** | 正式任务与发布协议由 01 发布 | 01 发布后再执行；在此之前不编造业务任务 |
| 4 | **端到端实跑** | `dsh --profile headless "<task>"` 未跑过（会初始化 headless profile、发起模型调用） | 操作者明确授权一次受控 smoke，或提供一个已有凭据的隔离 profile |
| 5 | **审批链路** | headless 没有实时审批通道；本框架使用 `--approval-policy never`（= 拒绝需要人工批准的调用，不是绕过审批） | 若将来要放开需人工批准的动作，必须由 01 另行设计，不能由本执行器自行放宽 |
| 6 | **发布者签名** | 仓库当前提交均为未签名（`git log %G?` = `N`） | 若要用签名规则，01 需配置签名并对清单/任务提交签名 |
| 7 | **回执路径迁移** | IOS-001 用的是 `results/IOS-001.md` 平铺路径；本框架用 `results/<task>/r<rev>/a1.md` | 由 01 确认新路径，或同步调整协议 |

---

## 8. 本次实际执行过的命令（摘要）

```text
# 只读：产品版本与入口（ASAR 内读取 + 启动器自述）
ELECTRON_RUN_AS_NODE=1 "<DSH_NODE_EXECUTABLE>" <probe.js>          # exit 0，读出 @deepseek-ai/dsh 0.2.2-rc.3
"<DSH_NODE_EXECUTABLE>" "<DSH_INSTALL_DIR>\lib\bin.js" --version   # exit 0，0.2.2-rc.3
"<DSH_NODE_EXECUTABLE>" "<DSH_INSTALL_DIR>\lib\bin.js" --help      # exit 0，含 headless 示例

# 框架自检
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --verify-entry
                                                                   # exit 0，product ok、help_ok、version_allowed
py -3.12 automation/bin/dsh_worker.py --config automation/config/automation.json --once
                                                                   # exit 0，真实分支上 protocol_not_ready（只读）
py -3.12 automation/tests/run_tests.py                             # exit 0，19/19
py -3.12 automation/bin/setup_mock_lab.py                          # exit 0
py -3.12 automation/bin/dsh_worker.py --config automation/mocklab/config/automation.mock.json  # 常驻中
py -3.12 automation/bin/dsh_control.py --config ...status          # exit 0
```

未执行：任何 `weibo_*.py` / `weibo_*.js`、`frida`、设备连接、触摸、spawn、kill、注册、
凭据采集、`dsh --profile headless "<task>"` 实跑、安装工具/服务。

---

## 9. 下一步（需 01 或操作者决定，本回执不构成授权）

1. 01 发布 `manifest/releases.json` 协议与 IOS-002 任务单，`scopes` 建议先只写
   `framework-development` / `offline-testing`。
2. 操作者核对清单后写入信任规则；建议至少同时钉 `pinned_commit`，避免只依赖内容摘要。
3. 在上述两项就绪后，先跑 `--mode live --once` 的受控 smoke（单个任务、只读型），
   确认 `attempt_harness_exit` 与 `final.reason.kind` 判定符合文档，再开常驻。
4. 若要放开任何需要人工批准的动作，必须单独设计审批通道；本框架不会代替审批。

---

本回执不产生新的执行许可。mock 通过 ≠ 真实自动闭环完成。
