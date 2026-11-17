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
| SMOKE-001 | r1 | 已准备，默认不执行 | IOS-AUTO-SMOKE-001 只读短文本 | [tasks/IOS-AUTO-SMOKE-001.md](tasks/IOS-AUTO-SMOKE-001.md) | 未执行 | 未跑 |
| AUTO-CONNECT-001 | v1 / r2 | 已验收：补测通过；等待器在 dry-run 下不代跑 | 签名门禁与等待器 | [tasks/AUTO-CONNECT-001-r2.md](tasks/AUTO-CONNECT-001-r2.md) | [results/AUTO-CONNECT-001/r2/a1.md](results/AUTO-CONNECT-001/r2/a1.md)（`8d8ba568293bddfd5c73cd36c7c4b65e89554901`） | [reviews/AUTO-CONNECT-001-r2-8d8ba56.md](reviews/AUTO-CONNECT-001-r2-8d8ba56.md) |
| AUTHORIZATION-001 | v1 | a4 已评审；SMOKE-001 r2 未发布 | 用户许可的受限发布公钥 | [automation/AUTHORIZATION-001.md](automation/AUTHORIZATION-001.md) | [a4](results/AUTHORIZATION-001/r1/a4.md)（`b7a042f`，未覆盖） | [a4 评审](reviews/AUTHORIZATION-001-a4-b7a042f.md) |

IOS-002 r1：blob SHA-1 `0ff8291afd777d7b64ea13c2480e9ccfca65ec70`；`content_sha256` `c709f134d2846fc51cc3dc1c4ce18f8ddb6f8244490a679ed6549cee7fc28ea8`。两个值不相等，不能互相替代。

IOS-002 r2：blob SHA-1 `9445ac7bb73ec4cb0209b0d55aee36793848bf1e`；`content_sha256` `e01f01a3bb4ac7751702bd46f10033676b769b981341d8f886c22d1ec57f6b47`。同 revision 内容若不再等于对应摘要，必须阻断。

AUTO-CONNECT-001 r1：blob SHA-1 `445a6ef779d2758a0d356f92b3fddd85ad17271a`；`content_sha256` `946310739b9a8be28b416428c1bf0784ff17552e842abd8b5bc9bbd346ebf779`。

一次连接说明 [automation/CONNECT_ONCE.md](automation/CONNECT_ONCE.md)：blob SHA-1 `283edb054417adcbc6d08de56ca95429c5a65cd5`；`content_sha256` `e62834c5951193dc5a5b1d6cd8765a5598631051c292704327859100cfe1925e`。

IOS-AUTO-SMOKE-001：blob SHA-1 `1be33135fd636216739f191e3c7cdac39f87c804`；`content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`。清单 task_id 是 `SMOKE-001`。任务提交 `8e9bcfb98526ba17ab6b6e7eca6d88c9072e930e`。

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
- a4 已收到（`b7a042f`）。自述 r1 已消费但未进入模型。`--patch` 顺序修复与官方启动器边界一致，但成功判定仍把任意 `final.text` 当成完成。**SMOKE-001 r2 未发布。** 见 [reviews/AUTHORIZATION-001-a4-b7a042f.md](reviews/AUTHORIZATION-001-a4-b7a042f.md)。

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
