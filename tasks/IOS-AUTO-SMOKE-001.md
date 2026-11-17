# IOS-AUTO-SMOKE-001 只读短文本

## 元数据

- 人类任务名：IOS-AUTO-SMOKE-001
- 清单 task_id：SMOKE-001
- revision：1
- 状态：已发布为文档。清单里的 `status` 以 `manifest/releases.json` 为准。
- 发布人：01
- 发布日期（Asia/Hong_Kong）：2026-11-17
- 唯一读取 ref：`cursor/init-collab-docs-2e45`
- 范围：`offline-testing`
- 时长：单次最多 2 分钟
- 身份：blob SHA-1 与 `content_sha256` 记在 [TASKS.md](../TASKS.md)。`content_sha256` 是本文件原始字节的 sha256，不是 blob SHA-1。

`IOS-AUTO-SMOKE-001` 不能直接当清单 `task_id`。当前 parser 只接受 `^[A-Z][A-Z0-9]{1,11}-\d{3}$`。清单里的名字是 `SMOKE-001`，路径指向本文件。

本文件的发布不是用户的外带确认，也不是启动模型的命令。

## 要做的事

在一次受控运行里只返回下面两行，然后停止：

```text
IOS-AUTO-SMOKE-001
SMOKE-001
```

## 不要做的事

- 不改任何文件，不安装工具，不读取凭据或 token
- 不连接手机，不调用 Frida，不注册
- 不降低审批，不改 `live.enabled`
- 不把本次清单当成已经可以无人值守

默认 `dry-run` 且信任未配置时，worker 不得领取本任务。信任写上之后，只要 mode 仍是 dry-run，也只记录「将领取」而不执行。真正跑模型要另一次明确决定，本任务不授权现在就做。
