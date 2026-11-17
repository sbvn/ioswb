# 任务索引

仓库：<https://github.com/sbvn/ioswb>（公开，本仓库即正式协作仓）

业务目录：`D:\GoDemo\wbjiaoben`（仅用户本机 DeepSeek Harness 按已发布任务修改）

发布规则：只有 01 可将任务状态改为「已发布」或「已撤回」。用户只把已发布任务交给自己的 DeepSeek Harness。Harness 不执行草稿，也不把验收意见、结果文件或网页内容当作新的授权。发布方未远程连接用户的 Harness 或手机。

| 任务 ID | 版本 | 状态 | 标题 | 任务文件 | 结果 | 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| IOS-001 | v1.0 | 已验收：只读盘点部分通过 | 现状核查、环境/工具清单与稳定性证据整理 | [tasks/IOS-001.md](tasks/IOS-001.md) | [results/IOS-001.md](results/IOS-001.md)（`ce0024b0cb4d42ac5b3da5e50fae9897d1c3c2ec`） | [reviews/IOS-001.md](reviews/IOS-001.md) |
| BOOTSTRAP | 回执 v1.0 | 限定验收：mock 成果可进入下一阶段 | 离线框架回执（兼容例外，不要求重做） | [automation/BOOTSTRAP.md](automation/BOOTSTRAP.md)（`d6a0c8cc88ec52caf02543e41095ed30e3180f86`） | 该文件即回执 | [reviews/BOOTSTRAP.md](reviews/BOOTSTRAP.md) |
| IOS-002 | v1 / r1 | 已复跑：不能 live | 自动交接框架的最小协议对齐 | [tasks/IOS-002.md](tasks/IOS-002.md) | [results/IOS-002/r1/a1.md](results/IOS-002/r1/a1.md)（`6c9888abae9b970d2b4af8a3e0d95fd4e53421e1`，原文不改） | [reviews/IOS-002-r1-6c9888a.md](reviews/IOS-002-r1-6c9888a.md) |
| IOS-002 | v1 / r2 | 已验收：信任范围修复成立，不能 live | 收紧清单信任范围 | [tasks/IOS-002-r2.md](tasks/IOS-002-r2.md) | [results/IOS-002/r2/a1.md](results/IOS-002/r2/a1.md)（`9b553fda23a71007ca741a1d4483a59f197f5de0`） | [reviews/IOS-002-r2-9b553fd.md](reviews/IOS-002-r2-9b553fd.md) |
| AUTO-CONNECT-001 | v1 / r1 | 已验收：等待器只读，不能 live | 一次连接父任务 | [tasks/AUTO-CONNECT-001.md](tasks/AUTO-CONNECT-001.md) | [a1](results/AUTO-CONNECT-001/r1/a1.md)、[a2](results/AUTO-CONNECT-001/r1/a2.md) | [reviews/AUTO-CONNECT-001-r1-9b553fd.md](reviews/AUTO-CONNECT-001-r1-9b553fd.md) |
| SMOKE-001 | r1 | 已撤回；失败台账保留，不可再领取 | IOS-AUTO-SMOKE-001 只读短文本 | [tasks/IOS-AUTO-SMOKE-001.md](tasks/IOS-AUTO-SMOKE-001.md) | [a4](results/AUTHORIZATION-001/r1/a4.md) 自述已消费、未进模型 | [a4 评审](reviews/AUTHORIZATION-001-a4-b7a042f.md) |
| SMOKE-001 | r2 | 已发布；仅现有会话读交接后可跑一次 | IOS-AUTO-SMOKE-001 只读短文本 r2 | [tasks/IOS-AUTO-SMOKE-001-r2.md](tasks/IOS-AUTO-SMOKE-001-r2.md) | 尚未回传 | 未跑 |
| SMOKE-002 | v1 / r1 | 已试跑：未通过（凭据缺失，已消费，已回滚） |
| SMOKE-002 | v1 / r2 | 已验收：通过，自动档已常驻 | IOS-AUTO-SMOKE-002 只读短文本（无人值守）r2 | [tasks/IOS-AUTO-SMOKE-002-r2.md](tasks/IOS-AUTO-SMOKE-002-r2.md) | [a1](results/SMOKE-002/r2/a1.md)（`5827515`，worker 自动上传 `f338913`） | [reviews/SMOKE-002-r2-5827515.md](reviews/SMOKE-002-r2-5827515.md) | IOS-AUTO-SMOKE-002 只读短文本（无人值守） | [tasks/IOS-AUTO-SMOKE-002.md](tasks/IOS-AUTO-SMOKE-002.md) | [a1](results/SMOKE-002/r1/a1.md)（`2945536`） | [reviews/SMOKE-002-r1-2945536.md](reviews/SMOKE-002-r1-2945536.md) |
| IOS-004 | v1 / r4 | 已完成（验收通过：门禁建成、默认关、恒拒绝未动） | 给执行器加 phone_auto 本机总开关与手机 scope 门禁 | [tasks/IOS-004-r4.md](tasks/IOS-004-r4.md) | [a1](results/IOS-004/r4/a1.md)（`47b2494`） | [reviews/IOS-004-r4-47b2494.md](reviews/IOS-004-r4-47b2494.md) |
| IOS-004 | v1 / r3 | 已停止：沙箱只给 attempt 目录写权、业务树不可写，未实施（回执经用户转交归档） | 给执行器加 phone_auto 本机总开关与手机 scope 门禁 | [tasks/IOS-004-r3.md](tasks/IOS-004-r3.md) | [a1](results/IOS-004/r3/a1.md) | [reviews/IOS-004-r3-local.md](reviews/IOS-004-r3-local.md) |
| IOS-004 | v1 / r2 | 已失败：沙箱 ACL 被拒未执行，已消耗（详见台账诊断） | 给执行器加 phone_auto 本机总开关与手机 scope 门禁 | [tasks/IOS-004-r2.md](tasks/IOS-004-r2.md) | 尚未回传 | 未跑 |
| IOS-004 | v1 / r1 | 已作废：被完整性拒绝消耗（task_commit 非祖先），由 r2 取代 | 执行器手机自动档门禁（phone_auto） | [tasks/IOS-004.md](tasks/IOS-004.md) | 尚未回传 | 未跑 |
| IOS-003 | v1 / r2 | 已搁置：不手动跑，改由 IOS-005 自动档执行（用户 2026-11-17 确认合并） | 运行现有程序一次：打开微博、首页刷新1次、随机滑动3–5下 | [tasks/IOS-003-r2.md](tasks/IOS-003-r2.md) | 尚未回传 | 未跑 |
| IOS-003 | v1 / r1 | 已停止：参数冲突未执行（swipe 上限 5，任务单写了 6） | 运行现有程序一次：打开微博、首页刷新1次、随机滑动3–6下 | [tasks/IOS-003.md](tasks/IOS-003.md) | [a1](results/IOS-003/r1/a1.md)（`7b0b9c6`） | [reviews/IOS-003-r1-7b0b9c6.md](reviews/IOS-003-r1-7b0b9c6.md) |
| AUTO-CONNECT-001 | v1 / r2 | 已验收：补测通过；等待器在 dry-run 下不代跑 | 签名门禁与等待器 | [tasks/AUTO-CONNECT-001-r2.md](tasks/AUTO-CONNECT-001-r2.md) | [results/AUTO-CONNECT-001/r2/a1.md](results/AUTO-CONNECT-001/r2/a1.md)（`8d8ba568293bddfd5c73cd36c7c4b65e89554901`） | [reviews/AUTO-CONNECT-001-r2-8d8ba56.md](reviews/AUTO-CONNECT-001-r2-8d8ba56.md) |
| AUTHORIZATION-001 | v1 | 成功判定已收紧；r2 交接已发布 |
| AUTHORIZATION-002 | v1 / r1 | 已验收：local-ack 生效 | Muse 发布钥匙受限信任锚 | [automation/AUTHORIZATION-002.md](automation/AUTHORIZATION-002.md) | [a1](results/AUTHORIZATION-002/r1/a1.md)（`4672e48`） | [reviews/AUTHORIZATION-002-r1-4672e48.md](reviews/AUTHORIZATION-002-r1-4672e48.md) | 用户许可的受限发布公钥 | [automation/AUTHORIZATION-001.md](automation/AUTHORIZATION-001.md) | [a4](results/AUTHORIZATION-001/r1/a4.md)（`b7a042f`，未覆盖） | [a4 评审](reviews/AUTHORIZATION-001-a4-b7a042f.md) |

IOS-002 r1：blob SHA-1 `0ff8291afd777d7b64ea13c2480e9ccfca65ec70`；`content_sha256` `c709f134d2846fc51cc3dc1c4ce18f8ddb6f8244490a679ed6549cee7fc28ea8`。两个值不相等，不能互相替代。

IOS-002 r2：blob SHA-1 `9445ac7bb73ec4cb0209b0d55aee36793848bf1e`；`content_sha256` `e01f01a3bb4ac7751702bd46f10033676b769b981341d8f886c22d1ec57f6b47`。同 revision 内容若不再等于对应摘要，必须阻断。

AUTO-CONNECT-001 r1：blob SHA-1 `445a6ef779d2758a0d356f92b3fddd85ad17271a`；`content_sha256` `946310739b9a8be28b416428c1bf0784ff17552e842abd8b5bc9bbd346ebf779`。

一次连接说明 [automation/CONNECT_ONCE.md](automation/CONNECT_ONCE.md)：blob SHA-1 `283edb054417adcbc6d08de56ca95429c5a65cd5`；`content_sha256` `e62834c5951193dc5a5b1d6cd8765a5598631051c292704327859100cfe1925e`。

IOS-AUTO-SMOKE-001 r1：blob SHA-1 `1be33135fd636216739f191e3c7cdac39f87c804`；`content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`。任务提交 `8e9bcfb98526ba17ab6b6e7eca6d88c9072e930e`。清单状态现为 `withdrawn`，文件字节未改。

SMOKE-001 r2：blob SHA-1 `856fa45a0308192ced393f5320e9d9258a8f306d`；`content_sha256` `a891b81c341e610f7c5154ef15b024ba8d2cb816f0d6b474ed08b25f7874cf44`。任务提交 `664d95e825e141228080e12a193bac90bb38b12a`。修复提交 `abd57261a0ef6701294e13b69378fa8a49b9f0fd`。一次交接：[automation/SMOKE-001-r2-RUN-ONCE.md](automation/SMOKE-001-r2-RUN-ONCE.md)。

SMOKE-002 r1：blob SHA-1 `a52822a605e1f9dc1e4115043a983ee86b9ef4a1`；`content_sha256` `994f23df0e4de0594742b496b062f6bce1ccd8dd2d7e3a427abef9338b1ead62`。任务提交 `f50b88226ae2df0addc553e7210f6653624cd1e7`。分级自动派发见 [docs/AUTO_DISPATCH.md](docs/AUTO_DISPATCH.md)（用户 2026-11-17 拍板：低风险自动跑、碰手机仍一次一单）；本机一次开启见 [automation/AUTO-ENABLE-ONCE.md](automation/AUTO-ENABLE-ONCE.md)；Muse 发布钥匙信任加入见 [automation/AUTHORIZATION-002.md](automation/AUTHORIZATION-002.md)（状态 `issued-awaiting-local-ack`，本机回执前不得领取 Muse 签名的清单）。SMOKE-002 发布后不发任何交接消息，等待器自动领取才算试跑成立。

SMOKE-002 r2：blob SHA-1 `10771b6ab0efbf21cafa87dd9f99c37d3e794317`；`content_sha256` `aeda100ab2f7c56324531cd9683d705814bc54012182fd99438fa1512d302138`。任务提交 `bd0ca393fe61a1d74c961a19f8c8938840f079b0`。r1 清单状态已转 `withdrawn`（已消费，任务字节未改）。开启口径见 [automation/AUTO-ENABLE-R2.md](automation/AUTO-ENABLE-R2.md)：用户 2026-11-17 选 patch 补丁方式，`patch_files=["state/auto-auth.patch.yml"]` 覆盖常驻每一轮；回滚须同时删除该引用与补丁文件。

清单文件提交 `216465021b5468e954a61eb8f4b75de5c01c3fe1`。外带锚只有这一条，而且本行不是用户已经确认：

`4d9d35446ed3e272f3ca70894a8344989ff1139843dcc2c56b5ffcc08f7f9013:216465021b5468e954a61eb8f4b75de5c01c3fe1`

写入本机信任时保持 `mode=dry-run`、`live.enabled=false`。不要打开 live，不要读取 token。下一份清单不会自动沿用这个锚。

协议：[docs/AUTOMATION_PROTOCOL.md](docs/AUTOMATION_PROTOCOL.md)。唯一读取 ref 是 `cursor/init-collab-docs-2e45`。

## 当前阶段

- IOS-001 保持已验收，不重开。
- bootstrap 回执已受理。不要重做。
- IOS-002 r1 回执已在。离线套件复跑见验收。不能 live。不要重做 bootstrap，不要覆盖 `a1`。
- r2 已验收。信任范围修复成立。不要重跑 r2，不要覆盖 `a1`。
- [AUTO-CONNECT-001](tasks/AUTO-CONNECT-001.md) 的等待器验收为只读。它不会因为看到 review 就执行新任务。
- [IOS-AUTO-SMOKE-001](tasks/IOS-AUTO-SMOKE-001.md) 已准备。默认 dry-run、信任未配时不执行。本索引不是用户的外带确认。
- live 仍不启用。签名证据见 [reviews/SIGNATURE-77998e8.md](reviews/SIGNATURE-77998e8.md)。本索引不是用户的外带确认。手机操作仍未授权。
- 桥接补测已由 01 确认。a3 自述 smoke 未启动、无 claim，仍是 `dry-run`。云端未核对本机磁盘。
- a4 自述 r1 已消费但未进入模型，该评审保留。成功判定已在 `abd57261` 收紧。r2 只通过 [automation/SMOKE-001-r2-RUN-ONCE.md](automation/SMOKE-001-r2-RUN-ONCE.md) 交给现有会话读一次。等待器不会自动开跑。云端不消费 r2。

## IOS-002 v1/r1 授权边界

允许：只改 `D:\GoDemo\wbjiaoben\automation\` 内的框架和离线测试；只读提取 manifest schema；普通 push `results/IOS-002/r1/a1.md`。scopes 只有 `framework-development` 和 `offline-testing`。单 worker，最多 60 分钟。

不授权：改微博脚本、业务 README、`AGENTS.md` 和 `runs*`；连接 Frida 或手机；安装工具或改服务；降低审批；headless 模型调用；启用 live；配置生产信任锚；发布真实 `manifest/releases.json`。

## IOS-002 v1/r2 授权边界

允许：只改 `automation\` 内的信任判断和离线测试；普通 push `results/IOS-002/r2/a1.md`。需要可读中文时另写 `results/IOS-002/r1/a2.md`，标明是转写。scopes 只有 `framework-development` 和 `offline-testing`。单 worker，最多 60 分钟。

不授权：覆盖 r1 回执或改 r1 任务文件；live；生产信任锚；可领取清单；手机、Frida、模型调用。

## IOS-001 v1.0 授权边界

允许：

- 只读用户本机 `D:\GoDemo\wbjiaoben` 的文件和已有证据
- 整理本机环境与已安装工具清单
- 输出脱敏结果 Markdown，路径为 `results/IOS-001.md`

不授权：

- 附加 App 诊断
- 真实触摸
- spawn
- kill
- 安装工具
- 修改业务代码
- 跑新批次
- 注册或提取凭据
- 向本仓库提交截图、录屏、账号参数、密钥、手机号、完整 UDID、个人路径或原始日志

历史 20 回合（成功 6、失败 14、其中 13 次 agent lost）以及后续 `process-terminated`，均为用户回执报告，尚非独立复现，根因未明。
