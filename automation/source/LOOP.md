# 持续调度入口

这是离线调度入口，不是本机已经在跑的常驻服务。云端没有启动用户机器上的 worker，也没有调用真实模型。

磁盘上的 `config/automation.json` 保持 `mode=dry-run`、`live.enabled=false`、`harness.unattended.enabled=false`。已保存登录不会被这个入口使用。审批保持 `never`。

## 一条离线演示

在仓库里执行：

```text
python3 automation/source/tests/demo_continuous.py
```

它会在临时目录生成合成 SSH 密钥和本地 file remote，跑 `bin/dsh_loop.py --dispatch --offline-run`，连续领取两个 fake 任务，上传原始回执和 `.meta.json`，然后写 STOP 并退出。不访问网络，不读真实凭据。输出里的 `DEMO PASS` 只说明这次云端自测通过。

## 本机以后要自己做的最小步骤

这些步骤这次没有替本机做：

1. 确认 `D:\GoDemo\wbjiaoben\automation\config\automation.json` 仍是 dry-run，且没有残留 `patch_files`。有残留就先删引用，不要改全局 `DSH_HOME`。
2. 只在本机 `automation/config/permits.json` 写下要跑的 `task_id`、`revision`、`scopes`、`budget`、`deadline`。`saved_login` 必须是 false。不要把已经消费的 SMOKE-001 r1/r2 再写进去。
3. 现有签名信任如果已经只覆盖这个仓库和分支，就继续用它。不要为了这次演示放宽规则。
4. 需要跑的时候再手动执行 `python automation/bin/dsh_loop.py --config automation/config/automation.json --dispatch --offline-run`。没有这两个开关就不会领取。
5. 停止用本机 `automation/state/STOP`。不要把它装成开机服务。

真实模型仍不在这个入口里。要改成真实 headless，需要另一次明确许可。
