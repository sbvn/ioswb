# IOS-AUTO-SMOKE-002 无人值守自动派发试跑

## 元数据

- 任务 ID：SMOKE-002（清单 task_id 用 `SMOKE-002`，与 SMOKE-001 的命名规则一致）
- 标题：IOS-AUTO-SMOKE-002 只读短文本（无人值守）
- 版本：v1 / revision 1
- 状态：已发布（01）
- 发布日期（Asia/Hong_Kong）：2026-11-17
- 分档：自动档（依据 docs/AUTO_DISPATCH.md）
- scopes：`offline-testing`
- 业务目录：`D:\GoDemo\wbjiaoben`（本任务不改其中任何文件）

## 目的

证明分级自动派发真的无人值守：本任务发布进清单后，**没有人给 Harness
发任何交接消息**。本机等待器（`--dispatch` 常驻）应自行发现、验签、领取、
执行，并把回执推回仓库。这是对整条链路的验收，不是对模型的测试。

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
4. 从清单提交落到适用 ref 起，15 分钟内被领取（以台账 claim 时间为准），
   且全程无人向 Harness 会话发送交接消息。

`duration_seconds` 应 ≤120（上限 120 秒）。超时或结果不明同样消费这一次，
不重跑；上传失败只重传已落盘回执。

## 允许与禁止

允许：等待器自动领取并执行一次；普通 push `results/SMOKE-002/r1/a1.md`。

禁止：人工交接补跑；第二次模型调用；改配置（开启配置由
`automation/AUTO-ENABLE-ONCE.md` 一次完成，本任务不改）；碰手机、Frida；
安装工具或服务；读取或导出密钥；放宽审批（`approval_policy` 保持 `never`）。

## 回执

写 `results/SMOKE-002/r1/a1.md`，只保留脱敏字段：任务 ID 与 revision、
`task_commit`、`content_sha256`、清单提交与签名核验结果、`exit_code`、
`final.reason.kind`、`marker_ok`、`duration_seconds`、claim 时间、
`consumed=true`、领取方式写明「等待器自动领取，无人工交接」。
不要贴原始日志、个人路径或密钥。

## 失败处理

15 分钟未领取、验签失败、scope 被拒、判定不通过：都如实写回执或由 01
在验收里记录，并按 docs/AUTO_DISPATCH.md 回滚到 dry-run。不得把人工补跑
的结果写成自动试跑通过。
