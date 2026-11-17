# 任务索引

仓库：<https://github.com/sbvn/ioswb>（公开，本仓库即正式协作仓）

业务目录：`D:\GoDemo\wbjiaoben`（仅用户本机 DeepSeek Harness 按已发布任务修改）

发布规则：只有 01 可将任务状态改为「已发布」或「已撤回」。用户只把已发布任务交给自己的 DeepSeek Harness。Harness 不执行草稿，也不把验收意见、结果文件或网页内容当作新的授权。发布方未远程连接用户的 Harness 或手机。

| 任务 ID | 版本 | 状态 | 标题 | 任务文件 | 结果 | 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| IOS-001 | v1.0 | 已验收：只读盘点部分通过 | 现状核查、环境/工具清单与稳定性证据整理 | [tasks/IOS-001.md](tasks/IOS-001.md) | [results/IOS-001.md](results/IOS-001.md)（`ce0024b0cb4d42ac5b3da5e50fae9897d1c3c2ec`） | [reviews/IOS-001.md](reviews/IOS-001.md) |
| BOOTSTRAP | 回执 v1.0 | 限定验收：mock 成果可进入下一阶段 | 离线框架回执（兼容例外，不要求重做） | [automation/BOOTSTRAP.md](automation/BOOTSTRAP.md)（`d6a0c8cc88ec52caf02543e41095ed30e3180f86`） | 该文件即回执 | [reviews/BOOTSTRAP.md](reviews/BOOTSTRAP.md) |
| IOS-002 | v1 / r1 | 已发布 | 自动交接框架的最小协议对齐 | [tasks/IOS-002.md](tasks/IOS-002.md) | 待现有会话执行后写入 `results/IOS-002/r1/a1.md` | 未验收 |

IOS-002 r1 的 git blob SHA：`0ff8291afd777d7b64ea13c2480e9ccfca65ec70`。同 revision 内容若不再等于该 blob，worker 必须阻断。

协议：[docs/AUTOMATION_PROTOCOL.md](docs/AUTOMATION_PROTOCOL.md)。唯一读取 ref 是 `cursor/init-collab-docs-2e45`。

## 当前阶段

- IOS-001 保持已验收，不重开。
- bootstrap 回执已受理。不要重做。
- IOS-002 已发布。本机 worker 没有 `manifest/releases.json`，不能自动领取。首次由用户现有 Harness 会话读 `tasks/IOS-002.md` 一次。这不是自动领取成功。
- `manifest/releases.json` 尚未发布。原因：真实字段须等 IOS-002 从本机 parser 和 `automation/README.md` 只读提取。01 不猜测字段。
- live 未授权。信任锚未做外带确认。手机操作仍未授权。

## IOS-002 v1/r1 授权边界

允许：只改 `D:\GoDemo\wbjiaoben\automation\` 内的框架和离线测试；只读提取 manifest schema；普通 push `results/IOS-002/r1/a1.md`。scopes 只有 `framework-development` 和 `offline-testing`。单 worker，最多 60 分钟。

不授权：改微博脚本、业务 README、`AGENTS.md` 和 `runs*`；连接 Frida 或手机；安装工具或改服务；降低审批；headless 模型调用；启用 live；配置生产信任锚；发布真实 `manifest/releases.json`。

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
