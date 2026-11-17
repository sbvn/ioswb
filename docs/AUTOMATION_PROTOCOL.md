# 自动任务交接协议

- 状态：不变量已定。`manifest/releases.json` 的字段待对齐，清单尚未发布。
- 发布人：01
- 日期（Asia/Hong_Kong）：2026-11-17
- 仓库：https://github.com/sbvn/ioswb
- 适用 ref：`cursor/init-collab-docs-2e45`

本协议不授权手机操作，不降低审批，也不代替具体任务单。执行许可仍只来自状态为「已发布」的任务。回执、验收和网页不能追加许可。

## 唯一 ref

worker 和 01 只读 `cursor/init-collab-docs-2e45`。不从 `main` 领取任务。更换 ref 必须由 01 修改本协议并另行发布。在此之前，其他分支上的文件都不是可执行清单。

## 轮询

- 01：每 5 分钟先看该 ref 的 HEAD 和文件变化，并查看兼容回执。当前兼容回执包括已受理的 `automation/BOOTSTRAP.md`，以及以后落在 `results/` 且绑定任务身份的回执。协议或清单缺失时，只报告阻塞，不编造清单，不猜测字段。
- 本机 worker：60 秒。没有可执行清单时记录阻塞并等待，不编造任务。

## 路径

与现有 worker 回执保持一致：

- 发布清单：`manifest/releases.json`
- 暂停旗标：`manifest/PAUSE`
- 不使用 `control/` 作为清单或暂停路径。本机控制入口如果仍叫 `executor/control.py`，那只是程序文件名，不是仓库控制面。

常规回执递归落在 `results/<task_id>/<revision>/a<n>.md`，并且绑定该任务的身份。`automation/BOOTSTRAP.md` 是已经受理的兼容例外，不要求重做，也不要求改放到 `results/`。`results/IOS-001.md` 保持原路径，不追溯改写。

## 身份

任务身份是 `task_id` + `revision` + 内容 hash。内容 hash 用该任务文件的 git blob SHA，或清单里与该 blob 绑定的 content hash。两者冲突时阻断。

`revision` 不变而内容 hash 变化：阻断。不执行，不把旧动作接着跑。

IOS-002 r1 的 blob SHA 以 [TASKS.md](../TASKS.md) 的记载为准。本协议不把作者名或文件标题当成身份。

## 锁

单 worker。一把操作系统排他锁从领取一直持有到本次尝试收尾。心跳只用于展示。心跳超时不抢锁，也不据此重跑。锁只在持有进程消失后由操作系统释放。

## 台账

持久台账只使用这些状态：

- `accepted`
- `running`
- `succeeded`
- `failed`
- `stopped`
- `recovery_required`

记录追加写入，并在落盘后保持。实现里的细项必须映射到这六个状态。映射写进对应回执。本协议不猜测本机现有 JSON 字段名；字段名以 IOS-002 从源码提取的结果为准。

## 结果

回执先在本机 spool 原子落盘，然后再上传。上传失败只重传已落盘的那一份，不重新执行任务。

旧动作的结果如果未知，不续跑，台账进入 `recovery_required`。不得把这种设计宣传成 exactly-once。

## STOP

STOP 跨重启仍然有效，并在三个时点生效：

1. 领取前
2. 执行中
3. 回执已落盘、尚未上传

必须确认执行器进程已经退出，才可以把台账记为 `stopped`。未确认退出时保持原状态，不开始下一次执行。

## 执行方式

默认单 worker，模式是 dry-run 或 mock。每个任务使用新的独立会话，并带有持久 handoff 和 context 预算。会话新建与否以源码和文档核对；在没有受控授权时不跑 headless 模型调用。

live 默认关闭。身份或信任锚尚不明确时，live 保持 blocked。不编造 GitHub 账号、密钥或信任材料。

## 信任

不能只靠提交作者名、Markdown 自称 01，或任意 Pull Request。

可用的方式只有：本机经外带渠道写入的 pin，或已经审验的签名。摘要钉、提交钉、签名指纹如果同时存在，摘要钉必须绑定到具体 commit，不能单独因为正文相似就放行。生产信任锚要由操作者外带确认，不由任务回执或本协议自动写入。

本分支已有提交的 `%G?` 为 `N`。在签名审验完成前，不把这些提交当作已签名发布。

## 清单字段

`manifest/releases.json` 尚未发布。原因：真实字段必须等 IOS-002 从本机 parser 和 `automation/README.md` 只读提取并核对。01 不在本文件猜测字段。

待对齐的只是清单字段。上面各节的 ref、轮询、路径、身份、锁、台账、结果、STOP、执行方式和信任规则已经固定。字段对齐不得改掉这些不变量。

执行方可以在 IOS-002 的回执之外，提交 `automation/contract/` 下的 JSON Schema 和 mock-only 样例。那不是已发布清单，也不能被 worker 当成 `manifest/releases.json` 执行。

## 当前阻塞

- 没有已发布的 `manifest/releases.json`，worker 不能自动领取。
- 信任锚未由外带渠道确认，live 不打开。
- IOS-002 已作为正式任务发布，首次由用户现有 Harness 会话阅读 `tasks/IOS-002.md` 一次。这次阅读不是自动领取成功。
- 之后 01 只用提取到的精确 schema 发布清单。用户再做一次外带信任锚确认后，才可能另发有范围的 live smoke。该 smoke 不在 IOS-002 的授权内。

## 范围与审批

手机、Frida、真实触摸、注册、凭据采集仍未授权。需要人工批准的调用保持拒绝，不得把拒绝策略改成绕过审批。每份任务自己的 scopes 白名单另写在该任务单中。
