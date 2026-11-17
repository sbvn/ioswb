# AUTHORIZATION-001 a3 限定评审

- 回执提交：`0934e2f64b19348985469c561dd049886bd2aadb`
- 父提交：`37e8667f679e11a8dfebd7e26750dd7b4b3e635f`
- 差异：只新增 `results/AUTHORIZATION-001/r1/a3.md`
- 评审：01，2026-11-17（Asia/Hong_Kong）

## 云端能核实的

该提交只增加 a3。`SMOKE-001` 的任务文件、清单 `216465021b5468e954a61eb8f4b75de5c01c3fe1` 和既有回执都没有被改。

官方标签 `dsh-v0.2.2-rc.3` 的提交是 `38a6a5c965aa99ab525161efb7cc5cf1fe62fced`。该标签上的 headless 中文说明和 CLI reference 确实写了 `--patch <path>`，以及 `credentials` / `authorization` / `deepseek-account` 三条 `disabled: false`。当前仓库快照里的 `HeadlessRunner.build` 没有把 `--patch` 放进参数。

## 只属于自述

a3 说本机 `claim` 为 0、全程 `dry-run`、`live.enabled=false`、headless 组合里那三行是 disabled、没有 API key、`~/.dsh/.credentials.yaml` 存在。云端没有看用户磁盘，这些都不能升格成独立核实。

a3 没有启动 smoke，因此没有消费那一次。这个「未启动」是回执结论；本机执行前仍要再查台账。

## 补充许可

用户已允许用官方局部 `--patch` 使用已保存登录，且只用于这一次 `SMOKE-001`。不许读取或导出密钥，不许改全局配置。说明见 [automation/AUTHORIZATION-001-LOCAL-AUTH.md](../automation/AUTHORIZATION-001-LOCAL-AUTH.md)。等待器不会因为这份说明自己开跑。
