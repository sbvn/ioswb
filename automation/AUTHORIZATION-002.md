# AUTHORIZATION-002 本机新增受限发布信任锚（Muse 发布钥匙）

- 状态：issued-awaiting-local-ack（云端已签发许可，本机回执确认前不生效）
- 日期（Asia/Hong_Kong）：2026-11-17
- 依据：用户 2026-11-17 决定由本聊天（Muse）担任 ioswb 发布通道，
  并询问如何授予推送权限。发布通道采用仓库 Deploy key（仅 sbvn/ioswb、
  可随时在 GitHub 仓库 Settings → Deploy keys 撤销）。

## 钥匙（公开信息，可入仓）

- 用途：仅用于向 `sbvn/ioswb` 的 `cursor/init-collab-docs-2e45` 分支推送，
  并对提交做 SSH 签名。
- 公钥：
  `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKwcPue2RR65ErfN/vKQD6mSvrj/Ppe/HehAxi/7FPpY muse-ioswb-deploy`
- 指纹：`SHA256:044wiJV/Aqh02gpC+/rpGB8ydtAQb5NOV4Ed1MW0/LE`
- 建议签名身份（allowedSigners principal）：`muse-ioswb-deploy`
- 私钥只存于 Muse 运行环境 `~/.ssh/id_ed25519_ioswb`，不入仓、不外传。

## 许可内容（仅此一项）

用户许可本机 DeepSeek Harness 在自己的 `config/trust/` 里**新增**一条
受限信任规则：接受以上指纹的 SSH 签名所签的清单提交，作为
`docs/AUTO_DISPATCH.md` 自动档的发布签名验真依据之一。

## 限制（不得扩大）

- 只新增这一条，不删改已有 cursor 发布钥匙的信任规则
  （`SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I` 保留）。
- 签名验真仍须同时满足原有全部条件：清单 `published`、`task_commit`
  为适用 ref 祖先、`content_sha256` 与任务字节一致、scope 在允许集内。
  签名通过不等于任何任务自动获批，人工档边界不变。
- 本许可不授权：改 scope 允许集、开手机/Frida 相关能力、降低审批、
  信任任何其他钥匙或作者名。
- 云端不写本机 `config/trust/`。本机写入后，须在回执
  `results/AUTHORIZATION-002/r1/a1.md` 里写明：已加入的指纹、principal、
  写入时间、写入前后的信任规则条数，并声明未改其他规则。
  该回执到达前，状态保持 `issued-awaiting-local-ack`，
  本机不得把 Muse 签名的清单当作已受信领取。

## 撤销

用户在 GitHub 删除该 Deploy key，或本机从信任规则中删除该指纹，
任一动作即撤销本通道；撤销后按 AUTOMATION_PROTOCOL 处理未决任务，
不追溯已按规则完成并验收的回执。
