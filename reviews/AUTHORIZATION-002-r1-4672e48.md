# AUTHORIZATION-002 r1 验收

- 回执：`results/AUTHORIZATION-002/r1/a1.md`，提交 `4672e48`
- 终审：01，2026-11-17（Asia/Hong_Kong）
- 结论：**通过。状态由 `issued-awaiting-local-ack` 转为 `local-ack` 生效。**

## 核对

| 项 | 结果 |
| --- | --- |
| 新增 identity / 指纹 | `muse-ioswb-deploy` / `SHA256:044wiJV/Aqh02gpC+/rpGB8ydtAQb5NOV4Ed1MW0/LE`，与 AUTHORIZATION-002 一致 |
| 公钥指纹复算 | 回执称以 `ssh-keygen -lf` 从公钥复算一致；云端此前已用同一公钥验过清单提交签名（Good），互相印证 |
| 作用域 | 限定 `sbvn/ioswb` + `cursor/init-collab-docs-2e45`，未放大 |
| 条数变化 | signers 1 → 2；原 cursor 规则未动；`allow` 三数组仍为空 |
| 自验 | 清单提交 `91f842a` 用新锚验签 Good、身份与指纹一致（与 SMOKE-002 回执中台账 `trust_rule=signed_manifest_commit` 互证） |
| 越界 | 未改 scope、未改业务脚本、未读私钥/token（均为回执自述，无反证） |

此后 Muse 通道签名的清单可被本机签名门禁验真。签名通过仍不等于任务获批，
其余条件（published、祖先、摘要、scope）不变。
