# AUTHORIZATION-001

- 状态：**issued-awaiting-local-ack**
- 日期（Asia/Hong_Kong）：2026-11-17
- 发布人：01。本文件传达用户本次明确许可。它不是 Git 文档自行授权，也不是本机已经接收。
- 仓库：https://github.com/sbvn/ioswb
- ref：`cursor/init-collab-docs-2e45`
- 清单：现有 [manifest/releases.json](../manifest/releases.json) 不改。`SMOKE-001` 的 `task_commit` 与 `content_sha256` 保持原值。

用户已明确允许：把下面这把已核验的发布公钥配进本机交接框架，只用于该仓库的指定协作分支；桥接补测由 01 独立确认通过之后，允许现有 Harness 对已发布的 `SMOKE-001` 做一次真实 headless，最多 120 秒。不操作手机，不安装工具，不读取凭据，不放宽审批。

云端没有配置本机信任文件，没有调用模型，也没有看到本机回执。在本机把实际指纹写入自己的台账之前，不得把同仓其他内容当成已经可信。

## 允许配置的公钥

- 身份：`cursoragent@cursor.com`
- 公钥：`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPqiJsBjAsv4KymedFcUR891X1lgC90DW8yMtjcHJ/p0`
- 指纹：`SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`

只核验签名，不读取私钥或 token。作者名和页面上的绿勾不够。

配置之后，持续自动范围只有 `framework-development` 与 `offline-testing`。任务正文不能把范围扩大。其他真实任务、系统服务和手机行为都不在本次许可内。

## 执行顺序

1. 本机 Harness 读到本文件后，先写 `results/AUTHORIZATION-001/r1/a1.md`，状态仍是 `issued-awaiting-local-ack` 或改为 `local-ack`。云端这一步还没发生。
2. 按已发布的 [tasks/AUTO-CONNECT-001-r2.md](../tasks/AUTO-CONNECT-001-r2.md) 做桥接和 mock / 离线测试。不要改该任务文件。
3. 等 01 在 `reviews/` 独立确认补测通过。执行方不能自批。
4. 只有第 3 步出现之后，已有 worker 才可以对 `SMOKE-001` revision 1、`content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8` 执行一次真实 headless。成功或失败都消耗这一次。结果不明则 `recovery_required`，不重跑。回执上传失败只重传。
5. 做完把代码里的 `mode` 恢复为 `dry-run`。

代码里的 `live` 只表示允许调用现有 headless。它不是手机权限。只可为这一次 `SMOKE-001` 临时打开，动作结束必须恢复 `dry-run`，避免以后的清单被自动扩大执行。

## 现有入口

不要再逐单复制。已经在跑的 [automation/CONNECT_ONCE.md](CONNECT_ONCE.md) 会话，下一轮只读扫描应看到本文件。能否衔接执行，取决于本机是否实现了 r2：用这把公钥验签、认 STOP、并且只放行清单里通过校验的任务。

当前 `connect_wait.py` 只扫描，不执行，也不读 STOP。这是唯一的实现阻塞。不能写成已经配置，也不能写成 smoke 已经跑过。

## 下一份回执必须写明

路径：`results/AUTHORIZATION-001/r1/a1.md`。之后的阶段用 `a2`、`a3`，不要覆盖这一份。

- 本机实际写入的信任指纹；没写就明确写「未配置」
- 桥接补测的命令、退出码，以及是否还在等 01 的独立确认
- `SMOKE-001` 是否已消费；未跑就写未跑
- `mode` 是否仍为 `dry-run`
