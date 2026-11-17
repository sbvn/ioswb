# AUTO-CONNECT-001 r2 验收

- 回执：`results/AUTO-CONNECT-001/r2/a1.md`，提交 `8d8ba568293bddfd5c73cd36c7c4b65e89554901`
- 集成版本：`c41d975cf76c964af86dc8844edf85144507ab8a`（只改了 `connect_wait.py` 的 phase 和 `SOURCE.md`）
- 终审：01，2026-11-17（Asia/Hong_Kong）
- 配置里的指纹和 `dry-run` 是回执自述。本验收没有查看用户磁盘。

## 结论

桥接补测通过。这不等于本机已经自动跑了 `SMOKE-001`。

`connect_wait.py` 只有在命令带 `--dispatch` 且配置 `mode` 不是 `dry-run` 时才调用 `Worker`（约第 244 行）。回执写明当前 mode 是 `dry-run`。因此这份验收**不会**让现有等待器自己执行 smoke。不能写成「已自动放行可运行」。

按已发布的 `automation/AUTHORIZATION-001.md`，本机 Harness 现在可以自己做这一次：对 `SMOKE-001` r1、`content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`、清单提交 `216465021b5468e954a61eb8f4b75de5c01c3fe1`，用已配置的公钥跑一次 headless，最多 120 秒，然后把 `mode` 恢复为 `dry-run`。代码不会自动恢复 mode。成功、失败都消耗这一次；结果不明不重跑；上传失败只重传。不要再让用户复制任务。

## 独立复跑

隔离目录 `/tmp/r2b-layout/automation`，夹具文件，无 `DSH_*`。

`python3 tests/run_tests.py`：**37/37 通过，跳过 0，14.9 秒，退出码 0**。

套件外：

| 检查 | 结果 |
| --- | --- |
| 未签名提交 | 执行 0 |
| 改清单后不重新签名 | 执行 0，签名状态 `bad` |
| 换一把公钥 | 套件 `test_signature_gate_rejects_unpinned_signer` 通过 |
| `phone-operation` scope | 套件 `test_scope_denied_refused` 通过 |
| 清单里的 `command` / `args` | 不进入 mock 或 headless 的参数。headless 固定为 `node bin.js --profile headless --permission-mode workspace-write --approval-policy never --json -` |
| 只有正文写 trusted、没有 signers | `load_trust` 视为未配置，不放行 |
| 公开提交 `2164650` | `ssh-keygen -Y verify` 为 Good，指纹 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`。本地 `%G?=N` 仍只表示当时没配 allowedSigners |

STOP 跨重启、取消确认、同一任务只领取一次、上传失败只补传、fresh session 不传 `--session-id`，都在这 37 项里通过。云端没有调用 DSH，没有写本机 trust。
