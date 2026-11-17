# 框架源码快照（AUTO-CONNECT-001 r2 桥接后）

- 来源：用户本机 `D:\GoDemo\wbjiaoben\automation\`
- 快照时间（Asia/Hong_Kong）：2026-11-17
- 用途：让团队独立静态阅读实现，不必只依赖回执自述
- 这不是运行中的代码副本，也不参与执行

## 已排除

- `config/automation.json` 与 `config/trust/publishers.json`（真实配置值与受限信任锚）
- `state/`、`outbox/`、`mocklab/`、`tests/.work/`（运行产物）
- `automation/BOOTSTRAP.md`（已单独入库）

## 本轮变化（AUTO-CONNECT-001 r2）

- 新增 `executor/sigverify.py`：SSH 签名核验（`git verify-commit` + allowedSigners，身份与指纹双匹配，指纹从公钥复算）
- `executor/trust.py`：信任文件新增 `signers`（受限公钥）并参与清单级判定
- `executor/worker.py`：清单提交用真实签名核验，替代 `%G?` 直读
- `bin/connect_wait.py`：每轮先读 STOP、STOP 跨重启、可派发给 worker（dry-run 不派发）
- `tests/`：新增 5 个桥接用例（签名接受/拒绝、STOP 跨重启、不重复领取、fresh session）

## 文件与哈希

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| `automation/source/executor/__init__.py` | 18 | `baa7c09c1efc7ac6753a669a6df996d670bfcc3134731bbdbc408cd58d871f33` |
| `automation/source/executor/common.py` | 164 | `a1826e6b2db2382d99c21556e835c6aafd96611564f1ad6fa9086e989a99c7a7` |
| `automation/source/executor/config.py` | 291 | `63d12754abc8ac2906ebbfae8ba77b6cc370084c7e82b519a398617d78e24fe2` |
| `automation/source/executor/control.py` | 112 | `6a6cd7b37eb82c207eb39fb5a1fb667cb748bd3bc611f622585f072c0d7f2b1f` |
| `automation/source/executor/gitrepo.py` | 175 | `c371c615399445c73c99b2853f285b8353d09ecd80e96aaa2b744deedeabcf20` |
| `automation/source/executor/handoff.py` | 126 | `761a5f10d2448c75b69f80fb90a4bad08223b808bafa659a95233401b15b56d0` |
| `automation/source/executor/ledger.py` | 206 | `7a93e53eb43e7ebc367061f81aefd78c9b7bbe4a1a6490b5f580984a9f88d57d` |
| `automation/source/executor/locking.py` | 77 | `10afffc2e429f38d27a19c668e47d06f16b7de80326b2dce6ffbc516c5a97e9b` |
| `automation/source/executor/manifest.py` | 143 | `b7a625b85b4b629fcb509132d47d47a9f6937836cea12199900e88504c6b7515` |
| `automation/source/executor/redact.py` | 85 | `dad425e60fdc0dd327b8c803e0582c0c80dfb383ce24c457ec0ed71b48644c89` |
| `automation/source/executor/runner.py` | 317 | `86afc0b6a866c18f37603534e5c348f860e467dbf81da583ee60b7134322fe93` |
| `automation/source/executor/sigverify.py` | 170 | `af4b48596a7174a1c8c451230002880d93e037102572def0c50825adc2b22d0c` |
| `automation/source/executor/trust.py` | 199 | `61225c6d9dc3d998b072dba71766fec3d7429d203c46862f4a4a748faf3bed92` |
| `automation/source/executor/worker.py` | 682 | `7c1239dc12c7074368e4f8d9060eb46278d96b29e5502beba57b60379224622f` |
| `automation/source/bin/dsh_worker.py` | 62 | `44d3ee169472ab465e2667c43a72fafdafdeea0727f710d517a286ed24b9fff4` |
| `automation/source/bin/dsh_control.py` | 58 | `f595d8464337a439b9df6c62b8e86d4b5c468b150d9543422aa3f961624c5832` |
| `automation/source/bin/setup_mock_lab.py` | 175 | `0f4e9d1a2329d74a8c6d0bc5d558747acd7bf83da5be1dd4c0a86b2b0676f989` |
| `automation/source/bin/connect_wait.py` | 315 | `9a985a0cf61d7c46331b2c2833ffcf2963492bd81ee0c5ba685daa6890ecc1d3` |
| `automation/source/tests/lab.py` | 383 | `ac619f334d6ed631a79b73a894c469ce1a468e1bd801021269548f4adcd0ed1b` |
| `automation/source/tests/run_tests.py` | 844 | `34f9bbcb345a5a8fd0e5f4942fceabe40252b222f64e13d31a0996dee45a70e0` |
| `automation/source/tests/fake_harness.py` | 100 | `6143d68c2e40c3f4a70a170c3ed108042cc8c9948ce097edfdde8c2c32ce1108` |
| `automation/source/config/automation.example.json` | 51 | `e36f8c8476d6edab559ac8ca7eff25038d4d2a5900a53df1e83f3b8f97117b48` |
| `automation/source/config/trust/publishers.example.json` | 15 | `cdad5c766a6552ed37975e83ebfb27a61b3ac7bb75df620a03a839b201a7652f` |
| `automation/source/README.md` | 215 | `78e40f23bb3a74eecbf46a973e537c7be8bb6d4582bd44253c1e4fc6db694c43` |
| `automation/source/.gitignore` | 8 | `c452103ded1aa076061bc1f9b382bd4043954c73ffd213542c4c3f0ca243e4fc` |

## 说明

- 快照经 `executor/redact.py` 规则扫描：0 命中。
- 真实信任锚（受限公钥）不在快照内，只在回执里写身份与指纹。
