# AUTHORIZATION-001 阶段验收

- 回执：`results/AUTHORIZATION-001/r1/a1.md`（`79ae5ae`）、`a2.md`（`8d8ba56`）
- 授权文件 blob：`81797c5cd5696a1cb21001acaf0d3a749323d029`
- 状态：**01 已确认桥接补测。本机 smoke 仍未消费。**
- 终审：01，2026-11-17（Asia/Hong_Kong）

a1 写的是当时未配置信任。a2 自述已经写入指纹 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`，并且 `mode=dry-run`、smoke 未跑。这些配置值只来自回执，不是本验收对用户磁盘的检查。正文里的 `local-ack` 本身不构成签名通过。

01 确认：桥接的签名门禁、STOP、清单绑定和 fresh headless mock 已在 `c41d975` 的源码上复跑通过。详见 [AUTO-CONNECT-001-r2-8d8ba56.md](AUTO-CONNECT-001-r2-8d8ba56.md)。

因此授权顺序里的「补测经 01 确认」已经满足。下一次真实 headless 只允许：

- `SMOKE-001` revision `1`
- `task_commit` `8e9bcfb98526ba17ab6b6e7eca6d88c9072e930e`
- `content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`
- 清单提交 `216465021b5468e954a61eb8f4b75de5c01c3fe1`
- 公钥指纹 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`
- 最多 120 秒，一次
- 不碰手机，不安装，不读凭据，不放宽审批

`live` 若被临时打开，只表示这一次 headless，做完必须回到 `dry-run`。等待器在 `dry-run` 下不会代跑。回执写到 `results/AUTHORIZATION-001/r1/a3.md`，写明指纹、这次是否已消费、结束后的 mode。云端不假设它已经成功。
