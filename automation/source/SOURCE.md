# 框架源码快照（final 完成判定修复）

- 来源：用户本机 `D:\GoDemo\wbjiaoben\automation\` 的公开快照，加上本轮在云端改的判定
- 快照时间（Asia/Hong_Kong）：2026-11-17
- 用途：让本机按固定提交核对并采用 `runner.py` 与 `handoff.py`
- 这不是运行中的代码副本。云端没有调用模型，也没有读用户磁盘

## 已排除

- `config/automation.json` 与 `config/trust/publishers.json`（真实配置值与受限信任锚）
- `state/`、`outbox/`、`mocklab/`、`tests/.work/`（运行产物）

## 本轮变化

- `executor/runner.py`：成功必须同时满足退出码 0、恰好一条 `final`、`reason.kind` 严格等于 `completed`、以及非空回执。`final.text` 只用来取文本。缺 reason、error/aborted/cancelled、非零退出、无 final、坏 JSON、多条 final、空输出、回执与文本不一致，都 fail closed。`--profile` → `--patch` → app flags 的顺序保持不变。清单里的 command/args 不进 argv。
- `executor/handoff.py`：上下文写明文字本身不算成功。
- `tests/probe_final_gate.py`：16 条公开输入。修复前 10 条被旧实现标成 success；修复后 16/16 为期望状态。
- `tests/run_tests.py`：接入上述探针，并断言命令注入进不了 argv。

修复前同一探针：10 条假成功（`error` / `aborted` / `cancelled` / 缺 reason / `Completed` / 两条 final / 回执盖过 error / 文本不一致），6 条原本就失败或本来就该成功。修复后 16/16。全量套件在带业务文件占位的副本里，业务文件两项通过；其余 39 项在快照目录通过，2 项因目录不是业务树而跳过，没有失败。

## 采用时要核对的两个文件

| 文件 | 修复前 SHA256 | 修复后 SHA256 |
| --- | --- | --- |
| `executor/runner.py` | `bc0c2c205de690c70edfef14c218bea055c80c5e98649df00d7173ae8529b2c1` | `674535cac88c91bd1f41d0d27449e76b08df1bf584d7c9d7bd3cf46a58b41b56` |
| `executor/handoff.py` | `7df4f9f06e7494e6f9a924d02e7e1dccadb7191ad9066a5e80d7c77002c086c6` | `9eb7690ddaadb4b4e9dea36b80c66c83d76e61e4f18741b3bfbae543f6733484` |

本机文件既不是左列也不是右列时，停止，不要覆盖。

## 文件与哈希

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| `automation/source/executor/__init__.py` | 18 | `baa7c09c1efc7ac6753a669a6df996d670bfcc3134731bbdbc408cd58d871f33` |
| `automation/source/executor/common.py` | 164 | `a1826e6b2db2382d99c21556e835c6aafd96611564f1ad6fa9086e989a99c7a7` |
| `automation/source/executor/config.py` | 307 | `df0c04ef2f7bcf251f2d328989e2c59b9b5ba6954b24d02abc608af2f11397c6` |
| `automation/source/executor/control.py` | 112 | `6a6cd7b37eb82c207eb39fb5a1fb667cb748bd3bc611f622585f072c0d7f2b1f` |
| `automation/source/executor/gitrepo.py` | 175 | `c371c615399445c73c99b2853f285b8353d09ecd80e96aaa2b744deedeabcf20` |
| `automation/source/executor/handoff.py` | 129 | `9eb7690ddaadb4b4e9dea36b80c66c83d76e61e4f18741b3bfbae543f6733484` |
| `automation/source/executor/ledger.py` | 206 | `7a93e53eb43e7ebc367061f81aefd78c9b7bbe4a1a6490b5f580984a9f88d57d` |
| `automation/source/executor/locking.py` | 77 | `10afffc2e429f38d27a19c668e47d06f16b7de80326b2dce6ffbc516c5a97e9b` |
| `automation/source/executor/manifest.py` | 143 | `b7a625b85b4b629fcb509132d47d47a9f6937836cea12199900e88504c6b7515` |
| `automation/source/executor/redact.py` | 85 | `dad425e60fdc0dd327b8c803e0582c0c80dfb383ce24c457ec0ed71b48644c89` |
| `automation/source/executor/runner.py` | 409 | `674535cac88c91bd1f41d0d27449e76b08df1bf584d7c9d7bd3cf46a58b41b56` |
| `automation/source/executor/sigverify.py` | 170 | `af4b48596a7174a1c8c451230002880d93e037102572def0c50825adc2b22d0c` |
| `automation/source/executor/trust.py` | 199 | `61225c6d9dc3d998b072dba71766fec3d7429d203c46862f4a4a748faf3bed92` |
| `automation/source/executor/worker.py` | 682 | `7c1239dc12c7074368e4f8d9060eb46278d96b29e5502beba57b60379224622f` |
| `automation/source/bin/dsh_worker.py` | 62 | `44d3ee169472ab465e2667c43a72fafdafdeea0727f710d517a286ed24b9fff4` |
| `automation/source/bin/dsh_control.py` | 58 | `f595d8464337a439b9df6c62b8e86d4b5c468b150d9543422aa3f961624c5832` |
| `automation/source/bin/setup_mock_lab.py` | 175 | `0f4e9d1a2329d74a8c6d0bc5d558747acd7bf83da5be1dd4c0a86b2b0676f989` |
| `automation/source/bin/connect_wait.py` | 319 | `baf5cc6410c9438f6246583b19268a91749e14ee41134eb1528fa58813d0a399` |
| `automation/source/tests/lab.py` | 383 | `48d3c527184b75e604616f7e09188ff83b223800121a990fef8963a088dced72` |
| `automation/source/tests/run_tests.py` | 950 | `c8b78455c61308d87e23ae0e46fb037a6899e42170d10184ba63d5ca400255f9` |
| `automation/source/tests/probe_final_gate.py` | 220 | `5aaf2af0def91ad6929bc7f1ff8d0f6d8a55a9ec836a1d92442982469efec2d9` |
| `automation/source/tests/fake_harness.py` | 100 | `6143d68c2e40c3f4a70a170c3ed108042cc8c9948ce097edfdde8c2c32ce1108` |
| `automation/source/config/automation.example.json` | 51 | `e36f8c8476d6edab559ac8ca7eff25038d4d2a5900a53df1e83f3b8f97117b48` |
| `automation/source/config/trust/publishers.example.json` | 15 | `cdad5c766a6552ed37975e83ebfb27a61b3ac7bb75df620a03a839b201a7652f` |
| `automation/source/README.md` | 215 | `78e40f23bb3a74eecbf46a973e537c7be8bb6d4582bd44253c1e4fc6db694c43` |
| `automation/source/.gitignore` | 8 | `c452103ded1aa076061bc1f9b382bd4043954c73ffd213542c4c3f0ca243e4fc` |

## 说明

- 表内哈希是当前文件字节的 sha256，不是 git blob SHA-1。
- 快照经 `executor/redact.py` 规则扫描的对象仍是源码，不含密钥。
- 真实信任锚与本地登录配置都不在快照内。
