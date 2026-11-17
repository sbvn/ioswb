# IOS-AUTO-SMOKE-001 只读短文本 r2

## 元数据

- 人类任务名：IOS-AUTO-SMOKE-001
- 清单 task_id：SMOKE-001
- revision：2
- 状态：随 `manifest/releases.json` 发布。只有该清单里 `status=published` 的这一条可领取。
- 发布人：01
- 发布日期（Asia/Hong_Kong）：2026-11-17
- 唯一读取 ref：`cursor/init-collab-docs-2e45`
- 范围：`offline-testing`
- 时长：这一次最多 120 秒
- 修复提交：`abd57261a0ef6701294e13b69378fa8a49b9f0fd`
- 身份：`content_sha256` 是本文件原始字节的 sha256，不是 blob SHA-1。数值写在清单和 `TASKS.md`。

r1 已经消费，本文件不改 `tasks/IOS-AUTO-SMOKE-001.md`。不要重跑 r1，不要 ack r1，不要清空台账。

## 要做的事

在这一次运行里只给出下面两行，并把同样两行写入当前目录的 `RECEIPT.md`，然后停止：

```text
IOS-AUTO-SMOKE-001
SMOKE-001
```

两处去空白后必须相同。不要加标题、解释或第三行。

## 不要做的事

- 不改业务文件，不执行 shell 工具，不读取、打印或导出凭据
- 不操作手机，不调用 Frida
- 不放宽审批，不改全局配置
- 不把日志里出现文字当成成功

成功只认：进程退出码 0，且唯一 `final.reason.kind` 严格等于 `completed`，且输出就是上面两行。其他结果都是失败，这一次仍然消费，不重跑。
