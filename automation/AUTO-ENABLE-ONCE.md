# 自动档一次开启（本机执行）

- 日期（Asia/Hong_Kong）：2026-11-17
- 依据：用户 2026-11-17 拍板「低风险任务自动跑，碰手机的仍一次一单」；
  协议见 `docs/AUTO_DISPATCH.md`。
- 这是**唯一一次**开启交接。开启完成后等待器常驻，后续自动档任务不需要
  再逐单交接。云端不连接本机、不写本机配置；以下动作由用户本机完成
  （可交现有 DeepSeek Harness 会话读一次执行）。
- 与 SMOKE-001 r2 的区别：那次是跑完恢复 dry-run；这次是**常驻开启**，
  不恢复。只有触发回滚条件时才关，见文末。

## 开启前核对（任一不符就停，写回执，不要自行放宽）

1. 本机 `config/trust/publishers.json` 已含签名信任：指纹
   `SHA256:/ZGdxqU+YWGLYEplYKh2c36jVXjB1wQzjGRo7qwO46I`
   （AUTHORIZATION-001 本机已配，本次只核对，不重写、不新增规则）。
2. 本机 dsh headless 版本在 `harness.unattended.product_version_allow`
   允许列表内（当前为 `0.2.2-rc.3`）。版本对不上就停下报告，
   不要自行把新版本加进允许列表。
3. `approval_policy` 仍是 `never`，`permission_mode` 仍是 `workspace-write`。
4. 台账里 `SMOKE-002@r1` 没有 claim；本机 STOP 不存在（或已按用户决定解除）；
   仓库适用 ref 上没有 `manifest/PAUSE`。
5. `scope.allowed` 仍只有 `framework-development`、`offline-testing`。
   多一项就停。

## 开启动作（只改本机配置，不改代码）

在本机 `automation/config/automation.json` 中：

- `mode`：`dry-run` → `live`
- `live.enabled`：`false` → `true`
- `live.reason`：清空（非空会挡住 live 闸门）
- `harness.unattended.enabled`：`false` → `true`
- 超时保持 `limits.task_timeout_seconds=3600`、
  `harness.unattended.timeout_seconds=3600`，不动
- 其余字段一律不动（repo、branch、manifest_path、trust_file、scope）

然后以派发模式启动等待器（常驻）：

- 入口：现有 `connect_wait.py`，参数带 `--dispatch`
- 记录启动时间、进程号，并按既有规矩写明这是常驻启动；
  进程若退出，下次启动第一条记录写「上次已退出，之前不是常驻」

## 开启后立刻做的试跑

1. 确认清单里 `SMOKE-002` r1 已 `published`（由 01 发布，见发布顺序）。
2. **不要**给 Harness 会话发任何消息。等等待器自己领取。
3. 预期：一个轮询周期量级内出现 claim，`results/SMOKE-002/r1/a1.md`
   被推回仓库，判定四项全过（见任务单）。
4. 15 分钟未领取或判定不过：按回滚处理，如实记录，不人工补跑。

## 常驻期间的规矩

- 等待器只会自动跑自动档（清单已发布 + 签名验过 + 指纹对上 + scope 在
  允许集内 + 只写 `automation/` 与 `results/`）。
- 人工档任务即使出现在清单里，禁止 scope 会被执行器直接拒绝；
  需要跑时仍由 01 另发 RUN-ONCE、用户在场一次一单。
- 每次自动执行的回执都会推回 `results/`；01 在云端逐份验收。

## 急停（任一即可，立即生效）

- 本机放 STOP 文件（跨重启有效）；或
- 仓库适用 ref 上新增 `manifest/PAUSE`；或
- 停等待器进程并把配置改回：`mode=dry-run`、`live.enabled=false`、
  `harness.unattended.enabled=false`。

出现以下任一情况必须急停并回滚、写明原因：非自动档被领取、验签失败仍被
领取、同一 revision 跑了第二次、回执与任务不符却判成功、用户要求停止。
回滚不删台账、不清 claim、不覆盖已有回执。
