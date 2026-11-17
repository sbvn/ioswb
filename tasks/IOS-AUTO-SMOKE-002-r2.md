# IOS-AUTO-SMOKE-002 r2 无人值守自动派发试跑（补凭据口径）

## 元数据

- 任务 ID：SMOKE-002（清单 task_id 用 `SMOKE-002`）
- 标题：IOS-AUTO-SMOKE-002 只读短文本（无人值守）r2
- 版本：v1 / revision 2
- 状态：已发布（01）
- 发布日期（Asia/Hong_Kong）：2026-11-17
- 分档：自动档（依据 docs/AUTO_DISPATCH.md）
- scopes：`offline-testing`
- 业务目录：`D:\GoDemo\wbjiaoben`（本任务不改其中任何文件）
- 前一版：r1 已试跑未通过（`MISSING_CREDENTIAL`，已消费），
  验收见 `reviews/SMOKE-002-r1-2945536.md`。r1 不重跑。

## 与 r1 的唯一区别

任务正文、成功判定、回执路径规则都不变。只改开启口径：按
`automation/AUTO-ENABLE-R2.md`，常驻配置带上凭据补丁
`patch_files=["state/auto-auth.patch.yml"]`（三行恢复、无密钥），
让 headless 能用凭据服务里已保存的登录。r1 失败在第一次模型请求，
r2 验证补上凭据后整条链路能否跑完。

## 任务正文（Harness 执行内容）

只读短文本任务。不读业务文件、不写业务文件。回执正文去空白后必须正好是
下面两行，多一行少一行都算失败：

```text
IOS-AUTO-SMOKE-002
SMOKE-002
```

## 成功判定（四项同时成立）

1. 进程退出码 0；
2. 恰好一条 `final` 事件，且 `final.reason.kind` 严格等于 `completed`；
3. 回执正文去空白后正好是上面两行（`marker_ok=true`）；
4. 等待器在开启后 15 分钟内自动领取，且全程无人向 Harness 会话
   发送交接消息（开启指令本身不算交接）。

`duration_seconds` 应 ≤120。超时或结果不明同样消费这一次，不重跑；
上传失败只重传已落盘回执。

## 允许与禁止

允许：等待器自动领取并执行一次；普通 push `results/SMOKE-002/r2/a1.md`。

禁止：人工补跑；第二次模型调用；碰手机、Frida；安装工具或服务；
读取或导出密钥；改 `$DSH_HOME`；放宽审批（`approval_policy` 保持 `never`）；
改仓库里的任务与清单文件；动 r1 的台账记录。

## 回执

写 `results/SMOKE-002/r2/a1.md`，字段与 r1 回执相同，并额外写明：
本次领取时 `patch_files` 是否生效（只写有/无与补丁文件相对路径，
不写任何凭据内容）、清单签名核验结果、claim 时间、`consumed=true`。
不要贴原始日志、个人路径或密钥。

## 失败处理

任何失败如实写回执，并按 docs/AUTO_DISPATCH.md 与 AUTO-ENABLE-R2.md
回滚（包含删除 patch 引用与补丁文件）。不得把人工补跑写成自动通过。
