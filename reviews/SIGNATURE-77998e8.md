# 签名核对（纠正「提交未签名」）

- 日期（Asia/Hong_Kong）：2026-11-17
- 核对人：01
- 这不是用户对生产信任的确认，也不写入 `config/trust/`。

## 观察

本地 `git log %G?` 对下列提交显示 `N`，并打印 `gpg.ssh.allowedSignersFile needs to be configured`。同一本地对象的提交头里已经有 `gpgsig -----BEGIN SSH SIGNATURE-----`。因此 `N` 只说明这次 git 没有完成签名校验，不能写成「没有签名」。

GitHub API `GET /repos/sbvn/ioswb/commits/{sha}` 与本地 `gpgsig` 文本一致（去掉首尾空白后相同）。API 字段：`verified=true`，`reason=valid`，`committer.login=cursoragent`，邮箱 `cursoragent@cursor.com`。

| 提交 | API | 本地 gpgsig | ssh-keygen -Y verify |
| --- | --- | --- | --- |
| `77998e8b9f87a249de0e35525e0111e69c4748cc` | valid | 有 | Good |
| `216465021b5468e954a61eb8f4b75de5c01c3fe1` | valid | 有 | Good |
| `8e9bcfb98526ba17ab6b6e7eca6d88c9072e930e` | valid | 有 | Good |
| `f3eebdb909c30b3704aee082e966b43846f0436f` | valid | 有 | Good |

校验命令使用签名里带出的公钥，身份 `cursoragent@cursor.com`，namespace `git`，payload 用 API 的 `verification.payload`。四次都打印：

`Good "git" signature for cursoragent@cursor.com with ED25519 key SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`

`git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=... verify-commit 77998e8` 同样是 Good。

公钥（从签名解析，不是从账号密钥接口抄来的）：

`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPqiJsBjAsv4KymedFcUR891X1lgC90DW8yMtjcHJ/p0`

`GET /users/cursoragent/keys` 这次返回空数组。不把空数组解释成签名无效，也不把绿勾单独当成已配置的生产锚。

此前 [reviews/IOS-002-r2-9b553fd.md](IOS-002-r2-9b553fd.md) 里「没有真实签名公钥」这句作废。r2 的离线 32/32 和负例仍然有效。

## 一次确认要覆盖的范围

用户若另行确认，只覆盖：

- 仓库 `https://github.com/sbvn/ioswb`
- ref `cursor/init-collab-docs-2e45`
- 签名身份 `cursoragent@cursor.com`
- 指纹 `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`
- 上面这一行 ssh-ed25519 公钥
- 自动执行范围只有 `offline-testing` 的 `SMOKE-001`，单次不超过 120 秒，单 worker
- 不包含 live 切换、手机、安装、凭据

确认之后，同一公钥对新的清单提交再次验签即可，不必每份清单重新钉摘要。当前代码还不会做这件事。
