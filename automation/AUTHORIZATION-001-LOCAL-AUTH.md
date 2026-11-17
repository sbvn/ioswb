# AUTHORIZATION-001 局部登录补充

- 状态：**issued-awaiting-local-exec**
- 日期（Asia/Hong_Kong）：2026-11-17
- 发布人：01。这是用户本次明确许可的补充，不是本文件自己授权自己，也不是本机已经执行。
- 仓库：https://github.com/sbvn/ioswb
- ref：`cursor/init-collab-docs-2e45`
- 只追加这一次 `SMOKE-001`。不增加次数，不重置台账，不扩大范围。

用户允许现有 DeepSeek Harness 用官方局部配置，正常使用已经保存的登录，并且只用于已经授权的这一次 `SMOKE-001`。不许读取、打印或导出密钥文件。不改全局配置，不放宽审批，不操作手机。结束后恢复 `dry-run`。

这只解除「正常程序使用已保存登录」的阻塞。云端没有调用 DSH，没有看用户磁盘，没有改真实配置。

## 官方依据（已核对）

标签 `dsh-v0.2.2-rc.3` 指向提交 `38a6a5c965aa99ab525161efb7cc5cf1fe62fced`。

- [packages/bundle/headless/README.zh.md](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.3/packages/bundle/headless/README.zh.md) 写明：随附 headless 禁用 `credentials`、`authorization`、`deepseek-account`。要恢复存储认证，把下面三行放进 `$DSH_HOME/profiles/headless/cordis.patch.yml`，或放进 `--patch` 覆盖文件。
- [apps/cli/reference/README.md](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.3/apps/cli/reference/README.md) 写明组合顺序的最后一层是 argv 里的每个 `--patch <path>`。后层覆盖同行。示例是 `dsh --profile web --patch ./extra.yml`。

本次只用 `--patch <本项目 automation 内的文件>`。不要写 `$DSH_HOME/cordis.patch.yml`，也不要写 `$DSH_HOME/profiles/headless/cordis.patch.yml`。

覆盖文件只有这三行，不含任何密钥：

```yaml
- id: credentials
  disabled: false
- id: authorization
  disabled: false
- id: deepseek-account
  disabled: false
```

## 现有 worker 不能透传

`automation/source/executor/runner.py` 的 `HeadlessRunner.build` 当前参数只有：

`--profile headless --permission-mode <配置> --approval-policy <配置> --json -`

没有 `--patch`。清单字段也不能把命令或参数塞进这条 argv。因此现有等待器即使离开 `dry-run`，也不会带上这三行。

本机若要做这一次，只能在项目 `automation/` 里临时加上这一个官方 `--patch`，指向上述无密钥文件。做不到就停止并写明，不要改全局配置，不要安装，不要重新登录。`--approval-policy` 保持 `never`。

## 谁来做

仓库里的等待器在 `dry-run` 且 `dispatch=false` 时不会因为新 Markdown 自己执行。现有 DeepSeek Harness 会话需要读本文件一次。这不是另一个名叫 Harness 的 CI 插件。

执行前先看本机台账。已有 `claim`、已经执行，或结果不明，都不得重跑。a3 自述 `claim` 为 0，那是自述，本机仍要再查一次。

通过只读预检后，只用现有 worker 跑原 `SMOKE-001` r1 一次，最多 120 秒：

- `task_commit` `8e9bcfb98526ba17ab6b6e7eca6d88c9072e930e`
- `content_sha256` `aba337481a3912205b3fe826bd05c615b694db1db5ca50f06c6937b3004813f8`
- 清单提交 `216465021b5468e954a61eb8f4b75de5c01c3fe1`
- 公钥指纹仍是 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`

不要为了试登录再发一次模型请求。唯一的模型请求就是这次 `SMOKE-001`。成功或失败都消耗这一次。结果不明不重跑。上传失败只重传。`finally` 里恢复 `mode=dry-run`、`live.enabled=false`，并删掉临时 `--patch` 文件。配置检查通过不是模型成功。

预检可以确认桌面和 headless 使用同一个 `DSH_HOME`，但不要打印该路径里的值，也不要分享可能含密钥的 dump。

回执写 `results/AUTHORIZATION-001/r1/a4.md`：实际有没有执行、是否已消费、结束时的 mode、阻塞原因。自述要脱敏。
