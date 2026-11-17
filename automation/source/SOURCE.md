# 框架源码快照（IOS-002 r2 更新）

- 来源：用户本机 D:\GoDemo\wbjiaoben\automation\
- 快照时间（Asia/Hong_Kong）：2026-11-17
- 用途：让团队独立静态阅读实现，不必只依赖回执自述
- 这不是运行中的代码副本，也不参与执行

## 已排除

- config/automation.json、config/trust/publishers.json（真实配置值与信任材料）
- state/、outbox/、mocklab/、	ests/.work/（运行产物，含 state/connect/ 等待器台账）
- utomation/BOOTSTRAP.md（已单独入库）

## 本轮变化（r2）

- executor/trust.py、executor/worker.py：信任范围拆成清单级 + 任务级
- 	ests/run_tests.py、	ests/lab.py：新增两个信任用例；干净 HOME 可跑
- in/connect_wait.py：新增只读等待器（AUTO-CONNECT-001 用，标准库，不调用模型）

## 文件与哈希

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| utomation/source/executor/__init__.py | 18 | baa7c09c1efc7ac6753a669a6df996d670bfcc3134731bbdbc408cd58d871f33 |
| utomation/source/executor/common.py | 164 | a1826e6b2db2382d99c21556e835c6aafd96611564f1ad6fa9086e989a99c7a7 |
| utomation/source/executor/config.py | 290 | f55bd31ed420b00a38281a97792662d1d8da26c4034ed23df8eb58817561e6b1 |
| utomation/source/executor/control.py | 112 | 6a6cd7b37eb82c207eb39fb5a1fb667cb748bd3bc611f622585f072c0d7f2b1f |
| utomation/source/executor/gitrepo.py | 175 | c371c615399445c73c99b2853f285b8353d09ecd80e96aaa2b744deedeabcf20 |
| utomation/source/executor/handoff.py | 126 | 761a5f10d2448c75b69f80fb90a4bad08223b808bafa659a95233401b15b56d0 |
| utomation/source/executor/ledger.py | 206 | 7a93e53eb43e7ebc367061f81aefd78c9b7bbe4a1a6490b5f580984a9f88d57d |
| utomation/source/executor/locking.py | 77 | 10afffc2e429f38d27a19c668e47d06f16b7de80326b2dce6ffbc516c5a97e9b |
| utomation/source/executor/manifest.py | 143 | b7a625b85b4b629fcb509132d47d47a9f6937836cea12199900e88504c6b7515 |
| utomation/source/executor/redact.py | 85 | dad425e60fdc0dd327b8c803e0582c0c80dfb383ce24c457ec0ed71b48644c89 |
| utomation/source/executor/runner.py | 317 | 86afc0b6a866c18f37603534e5c348f860e467dbf81da583ee60b7134322fe93 |
| utomation/source/executor/trust.py | 187 | 58ff3afcb3c9659ea650610cb87618ca90278814dcc51312a03ad46baaf461d8 |
| utomation/source/executor/worker.py | 676 | ad3f5a6272bf33c5102eab74e4590ef067b993809856ccc61289cb1cc8349565 |
| utomation/source/bin/dsh_worker.py | 62 | 44d3ee169472ab465e2667c43a72fafdafdeea0727f710d517a286ed24b9fff4 |
| utomation/source/bin/dsh_control.py | 58 | f595d8464337a439b9df6c62b8e86d4b5c468b150d9543422aa3f961624c5832 |
| utomation/source/bin/setup_mock_lab.py | 175 | 0f4e9d1a2329d74a8c6d0bc5d558747acd7bf83da5be1dd4c0a86b2b0676f989 |
| utomation/source/bin/connect_wait.py | 220 | bce8168304227756ddf90a72ddfe6f42082426f54591e9a7adf388c6220e1e1f |
| utomation/source/tests/lab.py | 354 | 624328dd3d6eab1a78d9d88dd46f955e3456d72c9152f634ef7942d95b56b4b1 |
| utomation/source/tests/run_tests.py | 717 | c2d293475e5d869b437aa2c29f8bafe41caa9cae55bd2136b7584ea2c35ff16b |
| utomation/source/tests/fake_harness.py | 100 | 6143d68c2e40c3f4a70a170c3ed108042cc8c9948ce097edfdde8c2c32ce1108 |
| utomation/source/config/automation.example.json | 51 | e36f8c8476d6edab559ac8ca7eff25038d4d2a5900a53df1e83f3b8f97117b48 |
| utomation/source/config/trust/publishers.example.json | 15 | cdad5c766a6552ed37975e83ebfb27a61b3ac7bb75df620a03a839b201a7652f |
| utomation/source/README.md | 215 | 78e40f23bb3a74eecbf46a973e537c7be8bb6d4582bd44253c1e4fc6db694c43 |
| utomation/source/.gitignore | 8 | c452103ded1aa076061bc1f9b382bd4043954c73ffd213542c4c3f0ca243e4fc |

## 说明

- 快照经 executor/redact.py 规则扫描：0 命中。
- 测试里的假 UDID / 手机号 / 个人路径样例按片段拼接生成，源码里没有可直接命中的字面量。
