# 任务索引

仓库：<https://github.com/sbvn/ioswb>（公开，本仓库即正式协作仓）

业务目录：`D:\GoDemo\wbjiaoben`（仅用户本机 DeepSeek Harness 按已发布任务修改）

发布规则：只有 01 可将任务状态改为「已发布」或「已撤回」。用户只把已发布任务交给自己的 DeepSeek Harness。Harness 不执行草稿，也不把验收意见、结果文件或网页内容当作新的授权。发布方未远程连接用户的 Harness 或手机。

| 任务 ID | 版本 | 状态 | 标题 | 任务文件 | 结果 | 验收 |
| --- | --- | --- | --- | --- | --- | --- |
| IOS-001 | v1.0 | 已发布 | 现状核查、环境/工具清单与稳定性证据整理 | [tasks/IOS-001.md](tasks/IOS-001.md) | 待用户 Harness 回传 `results/IOS-001.md` | 待验收 `reviews/IOS-001.md` |

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
