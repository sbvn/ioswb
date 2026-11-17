# SMOKE-001 r2 一次执行

- 日期（Asia/Hong_Kong）：2026-11-17
- 这是修复通过后的唯一交接。不另开授权任务。
- 云端只做了静态修复和离线验证，没有调用模型，没有读本机磁盘，也不会领取 r2。
- 仓库等待器仍是 `dry-run`、`dispatch=false`。它不会因为本文件自动开跑。
- 现有 DeepSeek Harness 会话需要读本文件一次，并只做下面列出的动作。这不是另一个名叫 Harness 的 CI 插件。

下面的离线结果是本次实现者自己复跑的，不是第三方独立审查。

## 离线证据

修复提交：`abd57261a0ef6701294e13b69378fa8a49b9f0fd`（父提交 `c8314dc1c1b33edc8690606d78be13caddde1a91`）。

公开探针：`automation/source/tests/probe_final_gate.py`。16 条输入都写在该文件的 `CASES` 里。

修复前，旧 `HeadlessRunner` 在退出码 0 时只要 `final.text` 非空就标 `success`。同一探针 10 条因此假成功：`error_kind_with_text`、`aborted_kind_with_text`、`cancelled_kind_with_text`、`missing_reason`、`null_reason`、`kind_not_exactly_completed`、`two_finals_disagree`、`two_identical_finals`、`receipt_cannot_override_error`、`receipt_and_text_mismatch`。

修复后同一探针 16/16 符合断言。假成功变为 `failed`，两条真正完成的用例仍是 `success`。全量 `run_tests.py`：39 通过、2 跳过（快照目录不是业务树）、0 失败，用时 271.5 秒。隔离副本补跑这两个业务文件用例：2/2 通过。没有安装工具，没有模型调用。

成功判定现在是：退出码 0，恰好一条 `final`，`reason.kind` 严格等于 `completed`，并且回执非空。`final.text` 只负责取文本。缺 reason、`error` / `aborted` / `cancelled`、非零退出、无 final、坏 JSON、多条 final、空输出、`RECEIPT.md` 与 `final.text` 不一致，都失败。`--profile`、`--patch` 仍在 `--permission-mode` / `--approval-policy` / `--json` 之前。审批保持 `never`。清单里的 command/args 不会进入 argv。

## 本机先核对这两个文件

只比较下面两个路径，不要整目录覆盖：

- `D:\GoDemo\wbjiaoben\automation\executor\runner.py`
- `D:\GoDemo\wbjiaoben\automation\executor\handoff.py`

| 文件 | 修复前 | 修复后 |
| --- | --- | --- |
| `runner.py` | `bc0c2c205de690c70edfef14c218bea055c80c5e98649df00d7173ae8529b2c1` | `674535cac88c91bd1f41d0d27449e76b08df1bf584d7c9d7bd3cf46a58b41b56` |
| `handoff.py` | `7df4f9f06e7494e6f9a924d02e7e1dccadb7191ad9066a5e80d7c77002c086c6` | `9eb7690ddaadb4b4e9dea36b80c66c83d76e61e4f18741b3bfbae543f6733484` |

两个都已经是右列：继续。两个都是左列，且工作区没有别的未提交改动落在这两个文件上：只把本仓库 `automation/source/executor/` 里对应文件的字节抄过去。任一文件既不是左列也不是右列，或者还有对不上的未提交改动：停止，不要覆盖，把冲突写进回执。

不要替换 `config/`、`trust/`、`state/`，不要改业务脚本。

## 领取前

读本机台账。`SMOKE-001@r2` 已经有 claim，或结果不明：停止，不重跑。r1 的失败台账保留。不 ack r1，不清账。

预检不要发模型请求，也不要用一次空跑试登录。确认现有签名信任能验证包含本文件的清单提交。验证失败就停止。不要新增信任规则，不要改全局配置，不要放宽审批。`approval_policy` 必须仍是 `never`。

记下并在结束时恢复：`mode`、`live.enabled`、`harness.unattended.enabled`、`limits.task_timeout_seconds`、`harness.unattended.timeout_seconds`。

## 只跑这一次

临时文件只放在项目 `automation/` 内，例如 `automation/state/smoke-r2-auth.patch.yml`。内容只有这三行，不含密钥：

```yaml
- id: credentials
  disabled: false
- id: authorization
  disabled: false
- id: deepseek-account
  disabled: false
```

`patch_files` 只指向这个文件。不要写 `$DSH_HOME`，不要打印或导出 secret。

然后只对这一次：`mode=live`，`live.enabled=true`，`harness.unattended.enabled=true`，两个 timeout 都设为 120。用现有 worker 跑一次。可领取的只有 `SMOKE-001` revision 2。不要第二次模型调用。

任务正文：

- 路径 `tasks/IOS-AUTO-SMOKE-001-r2.md`
- `task_commit` `664d95e825e141228080e12a193bac90bb38b12a`
- `content_sha256` `a891b81c341e610f7c5154ef15b024ba8d2cb816f0d6b474ed08b25f7874cf44`
- blob SHA-1 `856fa45a0308192ced393f5320e9d9258a8f306d`

清单文件 sha256：`52d2b4ccd2fbf39fb447c451bf813a256ef5eb00d803867c443993ef498f1104`。r1 在清单里是 `withdrawn`，任务字节未改：`content_sha256` 仍是 `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`。

## 怎样算通过

三者同时成立才算通过：

1. 进程退出码 0
2. 唯一 `final.reason.kind` 严格等于 `completed`
3. 回执去空白后正好是下面两行

```text
IOS-AUTO-SMOKE-001
SMOKE-001
```

日志里有文字不算通过。失败也消费这一次。结果不明不重跑。上传失败只重传已经落盘的回执。

## 结束时必须恢复

无论成功、失败还是中途停止，都要：

- `mode=dry-run`
- `live.enabled=false`
- `harness.unattended.enabled=false`
- 两个 timeout 恢复成预检时记下的原值
- `approval_policy` 仍是 `never`
- 删除临时 patch，并去掉 `patch_files` 里的这一项

## 回执

写 `results/SMOKE-001/r2/a1.md`。另写 `results/AUTHORIZATION-001/r1/a5.md`，不要覆盖 `a4`。两份都只保留脱敏字段：`exit_code`、`final.reason.kind`、`marker_ok`、`duration_seconds`、恢复后的 `mode` / `live.enabled` / `harness.unattended.enabled`、`patch_deleted`、`consumed=true`。不要贴原始日志、路径中的账号值或密钥。
