# 自动档开启 r2：补凭据补丁（常驻授权）

- 日期（Asia/Hong_Kong）：2026-11-17
- 发布人：01
- 依据：用户 2026-11-17 17:01 在「patch 补丁」与「环境变量 DEEPSEEK_API_KEY」
  二选一中明确选 patch 补丁方式。
- 前因：SMOKE-002 r1 试跑未通过，根因 `MISSING_CREDENTIAL`
  （见 reviews/SMOKE-002-r1-2945536.md）。r1 的开启文件漏了凭据来源，本文件补上。
- 本文件取代 `automation/AUTO-ENABLE-ONCE.md` 作为开启口径；其余条款
  （五项核对、四字段改法、急停回滚）仍按该文件与 docs/AUTO_DISPATCH.md。
- 云端不连接本机、不写本机配置；动作由用户本机完成。

## 补丁文件（常驻期间保留，不再逐次删除）

在本机业务目录 `automation/state/auto-auth.patch.yml` 新建，内容只有
下面三条，不含任何密钥（与 SMOKE-001 r2 跑通时用的官方三行相同）：

```yaml
- id: credentials
  disabled: false
- id: authorization
  disabled: false
- id: deepseek-account
  disabled: false
```

作用：恢复 headless 组合里默认禁用的三项，让 Harness 使用它自己凭据
服务里已保存的登录。不得改写 `$DSH_HOME` 下的任何文件，不得读取、
打印或导出密钥。

## 配置增改（在 AUTO-ENABLE-ONCE 四字段之外多一项）

本机 `automation/config/automation.json`：

- `harness.unattended.patch_files`：设为 `["state/auto-auth.patch.yml"]`
  （相对 automation 根目录；执行器配置层会校验文件必须在 automation
  内且存在，不合规会直接拒绝启动）
- 其余仍按 AUTO-ENABLE-ONCE：`mode=live`、`live.enabled=true`、
  `live.reason` 清空、`harness.unattended.enabled=true`、超时 3600/3600 不动

## 授权范围

- 本补丁授权覆盖**常驻自动档期间的每一轮自动执行**，不限于某一个任务；
  这正是与 SMOKE-001 r2 一次性临时补丁的区别，依据是用户本次选择。
- 只覆盖自动档（scope 与写范围仍受 AUTO_DISPATCH 约束）。
  人工档、手机相关能力不因此获得任何凭据便利之外的扩大。
- 撤销方式：回滚时删除 `patch_files` 这一项配置并删除补丁文件，
  与改回 dry-run 同时完成；撤销后不得留残留引用。

## 开启前追加核对（在原五项之外）

1. 本机台账 `SMOKE-002@r2` 无 claim；r1 的 claim 与 attempt_failed 保留，
   不 ack、不清账、不重跑 r1。
2. 当前配置里没有残留的旧 patch 引用（r1 回滚后应为空）；有残留先报告，
   不要叠加。
3. 补丁文件字节与上面三条一致（多一条少一条都停）。

## 试跑与失败处理

开启后等待器自动领取 SMOKE-002 r2（见 tasks/IOS-AUTO-SMOKE-002-r2.md），
判定与 r1 相同。失败或 15 分钟未领取：按 AUTO_DISPATCH 回滚，并同时
执行上面的撤销方式（删 patch 引用与补丁文件），如实写回执，不人工补跑。
