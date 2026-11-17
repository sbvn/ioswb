# AUTO-CONNECT-001 r2 签名门禁与等待器

## 元数据

- 任务 ID：AUTO-CONNECT-001
- revision：r2
- 版本：v1
- 状态：已发布
- 发布人：01
- 发布日期（Asia/Hong_Kong）：2026-11-17
- 父任务：[tasks/AUTO-CONNECT-001.md](AUTO-CONNECT-001.md)（字节不改）
- 范围：只限 `D:\GoDemo\wbjiaoben\automation\`
- 唯一 ref：`cursor/init-collab-docs-2e45`
- 签名证据：[reviews/SIGNATURE-77998e8.md](../reviews/SIGNATURE-77998e8.md)

本文件不是用户已经确认生产信任。不要把指纹写进 `config/trust/`，不要开 live，不要调用模型。

## 现状

r2 的两级信任判断已经过独立复跑。`connect_wait.py` 只扫描远端，不执行任务，也不读 STOP。这还不是连续闭环。签名对象已经在提交里，但 worker 仍不会用这把公钥决定能不能跑。

## 本机要实现的四件事

1. 签名适配：用户确认之后，用 `ssh-keygen -Y verify` 或带 `allowedSigners` 的 git，核验清单提交的 SSH 签名。公钥指纹必须等于 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`，身份是 `cursoragent@cursor.com`。作者名、绿勾、未配置 allowedSigners 时的 `%G?=N` 都不算通过。
2. 等待器读 STOP：每轮扫描前看本机 STOP。STOP 在重启后仍然有效。退出时写下「已停止，不是常驻」。不得在打印任何模型命令后声称仍在运行。
3. 清单门禁：只执行同时满足这些条件的任务：清单 `status=published`、`content_sha256` 等于 `git show` 原始字节、`task_commit` 是 ref 祖先、清单提交签名通过第 1 条、scope 属于父任务允许集。已完成的 IOS-002 r2 不得再次领取。
4. fresh headless：每个这样的任务新建会话，不传 `--session-id`。在用户确认之前，用 mock 测这条路径，不调用真实 `dsh`。

确认前自动执行范围只有 `SMOKE-001` / `offline-testing`，单次最多 120 秒。确认的内容以签名证据文件为准。本任务的实现提交本身不构成确认。

## 允许与禁止

允许：改 `automation\` 内的等待器、信任校验和离线测试；普通 push `results/AUTO-CONNECT-001/r2/a1.md`。

禁止：改已固定的 `tasks/AUTO-CONNECT-001.md`、`tasks/IOS-002-r2.md`、`tasks/IOS-AUTO-SMOKE-001.md` 和已有回执；写生产信任文件；启用 live；跑模型；读取私钥或 token；新增系统服务；降低审批；碰手机。

## 验收

离线测试要证明：签名指纹不符则不领取；STOP 跨重启后不再扫描；已完成的 r2 不会被清单再次启动。回执写明命令和退出码，并写明真实 headless 仍未跑。
