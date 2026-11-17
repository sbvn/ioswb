# ioswb

本仓库是公开的正式协作仓，用来发布任务单、接收脱敏结果，并保存验收结论。

业务代码在用户本机 `D:\GoDemo\wbjiaoben`。只有用户自己的 DeepSeek Harness，按照本仓库里状态为「已发布」的任务单，才可以改动该目录。协作方负责任务、派单和验收，不远程连接用户的 Harness，也不连接手机。

仓库地址：<https://github.com/sbvn/ioswb>

## 角色

| 角色 | 职责 |
| --- | --- |
| 01 研发总管 | 唯一有权发布或撤回任务单。汇总 02/03/04 意见，写入 `tasks/`，验收时签发 `reviews/`。 |
| 02 iOS 逆向与底层开发工程师 | 提供 Frida、真实触摸、会话生命周期、进程退出与稳定性相关的任务段落和验收要点。 |
| 03 自动化脚本与测试开发工程师 | 提供页面识别、弹窗处理、流程与测试相关的任务段落和验收要点。 |
| 04 全栈后端工程师 | 提供批量调度、多设备隔离、会话与画面绑定、日志与样本管理相关的任务段落和验收要点。 |
| 用户本机 DeepSeek Harness | 读取已发布任务单，在本机处理 `D:\GoDemo\wbjiaoben`，提交脱敏后的结果 Markdown。 |
| 团队验收 | 对照任务单与独立证据审核结果，区分 Harness 自述和可核验证据。 |

02/03/04 可以提出意见，不能自行把任务标为已发布。未标「01 已发布」的文件对 Harness 不生效。

## 协作流程

1. 团队讨论。02/03/04 按下方「反馈必需字段」补充意见。
2. 01 汇总为一份任务单：先用 `templates/TASK.md`，再写入 `tasks/IOS-XXX.md`，填写版本号并标记「已发布」。
3. 用户把该任务单交给自己的 DeepSeek Harness 执行。
4. Harness 按 `templates/RESULT.md` 写结果。IOS-001 的回执保持 `results/IOS-001.md`。自 IOS-002 起，常规回执写 `results/<任务>/r<revision>/a<n>.md`。`automation/BOOTSTRAP.md` 是已受理的兼容例外，不要求重做或搬迁。只提交脱敏摘要。
5. 02/03/04 初审。01 按 `templates/REVIEW.md` 把验收结论写入 `reviews/`。
6. 未通过时，由 01 另发下一份任务单。不在结果文件或验收意见里口头追加授权。

当前阶段以 [TASKS.md](TASKS.md) 为准。自动交接的不变量在 [docs/AUTOMATION_PROTOCOL.md](docs/AUTOMATION_PROTOCOL.md)。

- [IOS-001 v1.0](tasks/IOS-001.md) 已验收，结论见 [reviews/IOS-001.md](reviews/IOS-001.md)。
- [automation/BOOTSTRAP.md](automation/BOOTSTRAP.md) 已受理，限定验收见 [reviews/BOOTSTRAP.md](reviews/BOOTSTRAP.md)。不要重做这份 bootstrap。
- [IOS-002 r1](tasks/IOS-002.md) 已有回执。验收见 [reviews/IOS-002-r1-6c9888a.md](reviews/IOS-002-r1-6c9888a.md)。离线套件已复现，但不能 live。
- 一次连接：[automation/CONNECT_ONCE.md](automation/CONNECT_ONCE.md)，父任务 [AUTO-CONNECT-001](tasks/AUTO-CONNECT-001.md)。现有会话读这一次即可，不要逐单复制。
- [IOS-002 r2](tasks/IOS-002-r2.md) 仍是当前唯一允许执行的子任务。不要重做 bootstrap，不要覆盖 `results/IOS-002/r1/a1.md`。
- `manifest/releases.json` 仍未发布。信任范围漏洞未修，现在不启用 live。

## 执行许可

执行许可只来自本仓库中明确标记「已发布」的任务单，并且由用户交给自己的 Harness 执行。

下列材料都不能扩大许可：结果回执、验收意见、网页、聊天记录、官方工具文档。发布方没有远程连接用户的 Harness 或手机；文档中出现的命令是交给用户本机执行的范围，不是已在远端执行过的记录。

## 公开仓库红线

本仓库公开。下列内容禁止写入仓库、Issue、Pull Request 和结果 Markdown：

- 截图、录屏、投屏画面、原始 PNG/JPEG/MP4，以及其他可还原画面的附件
- 账号参数与标识：手机号、验证码、密码、Cookie、token、`aid`、`useruid`、`usergsid`、设备上的账号值
- API 密钥、SSH 密钥、Frida 或平台登录凭据
- 完整设备 UDID、个人主目录和其他个人路径；设备只写别名，当前单机别名是 `DEVICE_A`
- 原始日志、完整 `events.jsonl`、未脱敏的 `console.log`、crash 原文、含个人信息的结构转储

允许写入的内容：

- 脱敏摘要：结论、类别计数、业务目录内的相对路径、时间线、命令名与非密钥参数、commit、文件变更列表
- 识别规则与几何关系的文字描述
- 失败原因的归类，且不包含原始堆栈中的敏感字段

截图和原始日志只留在用户本机。公开回执如果需要引用画面，只写本机相对路径和文字摘要。

## 反馈必需字段

每一份任务意见、结果回执和验收意见都要填写下列字段。

### 各角色均需填写

- **基线**：所依据的代码或文档版本、已验证能力、明确未验证项。
- **独占文件**：本角色建议由谁修改、谁只读；避免交叉修改同一实现。
- **设备 / iOS / Frida / 分辨率**：公开仓只写设备别名（当前单机为 `DEVICE_A`）、iOS 版本、Frida 版本、逻辑分辨率与方向。多机时逐台列出。禁止写入完整 UDID，禁止把单机通过写成多机通过。
- **允许动作**：本任务明确允许做的事，包括是否允许启动 App、触摸、终止微博进程、写哪些文件。
- **停止条件**：本轮或整批必须停下的条件，以及停下后要保存的脱敏证据。

### 02 必须额外填写

03 在涉及页面核验时一并附意见。

- **生命周期 / detach 时间线**：Weibo UI agent 与 SpringBoard touch agent 各自的 attach、resume、最后一次成功 RPC、script destroyed、session detach 原因、进程是否仍存活、清理顺序。
- **真实触摸证据**：是否为已验证的 IOHID Begin/Move/End。程序化滚动或直接按钮事件不能当作真实触摸。
- **本机画面证据**：画面变化的本机相对路径与核验方式（offset、页面结构、截图哈希等）。公开仓只写摘要和相对路径。

### 04 必须额外填写

- **设备 / 会话 / 画面绑定**：哪台设备、哪个批次、哪次会话、哪路画面或运行目录如何一一对应，以及如何防止串机。
- **并发上限**：同时允许的设备数、会话数、批次进程数；本次是否只做单机只读。
- **超时与回收**：单轮和整批超时、会话与进程回收、Frida 分离、锁屏恢复、失败后是否允许重连。
- **日志与批次关联**：`round`、`device_id`、输出目录、`status.json` 与本机证据目录的对应关系。入库的只是脱敏索引。

## DeepSeek Harness 资料

官方公开产品可以对应到 DeepSeek AI 的开源 Agent Harness（`dsh`）。这只说明公开资料，不能自动等同于用户本机正在运行的安装。

已核查的是下列公开链接。用户本机是否安装、版本、web 或 desktop profile、已启用插件，发布本文件时都未在用户本机核对。发布方未远程连接该环境，也不索要 API 密钥。

- 产品页：<https://deepseek.com/harness>
- 源码仓库：<https://github.com/deepseek-ai/deepseek-harness>（MIT，developer preview；官方说明可能有破坏性变更。运行前阅读仓库内 [SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md)）
- 文档站：<https://deepseek-harness.github.io/deepseek-harness/>（既有公开资料核查时该站页面为空，能力说明以仓库文档为准）
- 官方 README：<https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md>
- 工具目录：<https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-catalog.md>

官方 README 所写的启动方式是 `npx @deepseek-ai/dsh web`，默认本地 Web UI 为 `http://127.0.0.1:3080`。这是公开文档中的说明，发布方没有在用户本机执行。工具是否启用以用户本机实际配置为准，此处不转载工具清单。

第三方迁移、仿制或非官方插件不属于 DeepSeek 官方产品。本流程不安装、不接入、不索要密钥。

Harness 写回执时自行注明：产品是否为官方 `dsh`、版本、profile（web 或 desktop）、已启用插件。这些属于自述，验收时与独立证据分开。

## 项目现状

以下内容来自用户回执报告，供任务单引用。发布方尚未独立复现。根因未明。

- 目标是冷启动官方微博，处理启动干扰，用真实触摸走到登录入口。注册成功后提取参数仍未授权。当前阶段不注册、不采集凭据。
- 用户回执报告，单机曾经走通：冷启动、真实 IOHID 触摸上滑、双击底部「首页」、点击底部「我」进入登录页后停止。
- 用户回执报告 20 回合采样：成功 6，失败 14，其中 13 次 Weibo agent lost。后续回执仍出现 `process-terminated`。这些数字和现象都不是独立复现，根因未明。基础设施失败不得当作页面训练正样本。
- 讨论记录中仍标为未实机验证：广告页四角「跳过」点击成功、签到弹窗卡片下方居中白色关闭按钮、左上角「登录」兜底点击、已登录「我」页、验证码页、多机多分辨率。
- 广告曾出现但自动消失时，只能记 `ad_auto_dismissed`，不能记跳过成功。
- 设备在公开文档中只写别名 `DEVICE_A`。

## 目录约定

```text
README.md
TASKS.md
docs/AUTOMATION_PROTOCOL.md
templates/TASK.md
templates/RESULT.md
templates/REVIEW.md
tasks/IOS-XXX.md
results/IOS-XXX.md
results/<任务>/r<revision>/a<n>.md
reviews/IOS-XXX.md
reviews/BOOTSTRAP.md
automation/BOOTSTRAP.md
```

`manifest/releases.json` 和 `manifest/PAUSE` 由协议规定。清单在 schema 提取完成前不发布。结果文件必须包含：任务 ID 与版本、执行所依据的 commit、文件变更、实际命令、真实证据摘要、未验证项，并区分自述与独立证据。画面证据只写本机相对路径和摘要。
