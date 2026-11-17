# 框架源码快照（IOS-002 r1）

- 来源：用户本机  + "D:\GoDemo\wbjiaoben\automation\" + 
- 快照时间（Asia/Hong_Kong）：2026-11-17
- 用途：让团队可以独立静态阅读实现，不必只依赖回执自述
- 这不是运行中的代码副本，也不参与执行

## 已排除（按要求）

-  + "config/automation.json" + 、 + "config/trust/publishers.json" + （真实配置值与信任材料）
-  + "state/" + 、 + "outbox/" + 、 + "mocklab/" + 、 + "	ests/.work/" + （运行产物）
-  + "utomation/BOOTSTRAP.md" + （已单独入库，不重复快照）

## 文件与哈希

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| `automation/source/executor/__init__.py` | 9 | `baa7c09c1efc7ac6753a669a6df996d670bfcc3134731bbdbc408cd58d871f33` |
| `automation/source/executor/common.py` | 117 | `a1826e6b2db2382d99c21556e835c6aafd96611564f1ad6fa9086e989a99c7a7` |
| `automation/source/executor/config.py` | 246 | `f55bd31ed420b00a38281a97792662d1d8da26c4034ed23df8eb58817561e6b1` |
| `automation/source/executor/control.py` | 96 | `6a6cd7b37eb82c207eb39fb5a1fb667cb748bd3bc611f622585f072c0d7f2b1f` |
| `automation/source/executor/gitrepo.py` | 142 | `c371c615399445c73c99b2853f285b8353d09ecd80e96aaa2b744deedeabcf20` |
| `automation/source/executor/handoff.py` | 106 | `761a5f10d2448c75b69f80fb90a4bad08223b808bafa659a95233401b15b56d0` |
| `automation/source/executor/ledger.py` | 171 | `7a93e53eb43e7ebc367061f81aefd78c9b7bbe4a1a6490b5f580984a9f88d57d` |
| `automation/source/executor/locking.py` | 60 | `10afffc2e429f38d27a19c668e47d06f16b7de80326b2dce6ffbc516c5a97e9b` |
| `automation/source/executor/manifest.py` | 123 | `b7a625b85b4b629fcb509132d47d47a9f6937836cea12199900e88504c6b7515` |
| `automation/source/executor/redact.py` | 60 | `dad425e60fdc0dd327b8c803e0582c0c80dfb383ce24c457ec0ed71b48644c89` |
| `automation/source/executor/runner.py` | 269 | `86afc0b6a866c18f37603534e5c348f860e467dbf81da583ee60b7134322fe93` |
| `automation/source/executor/trust.py` | 119 | `42a32bb14608724bfe08ae31e1b626f42d27602cfc0e85e685dc75a41d2622f8` |
| `automation/source/executor/worker.py` | 559 | `c5acea34b0a4056098142848ead2e4f65886652dc7754019106908b12840a7d7` |
| `automation/source/bin/dsh_worker.py` | 48 | `44d3ee169472ab465e2667c43a72fafdafdeea0727f710d517a286ed24b9fff4` |
| `automation/source/bin/dsh_control.py` | 44 | `f595d8464337a439b9df6c62b8e86d4b5c468b150d9543422aa3f961624c5832` |
| `automation/source/bin/setup_mock_lab.py` | 142 | `0f4e9d1a2329d74a8c6d0bc5d558747acd7bf83da5be1dd4c0a86b2b0676f989` |
| `automation/source/tests/lab.py` | 302 | `6ef97d5554581429998ee2cac72fe984f9061824d9505a64ad542c38d92245c8` |
| `automation/source/tests/run_tests.py` | 504 | `99c7db97aa0cbb334f2142e859ffe8d81655d5e87d592ee0e3bd37b9e9d251e0` |
| `automation/source/tests/fake_harness.py` | 80 | `6143d68c2e40c3f4a70a170c3ed108042cc8c9948ce097edfdde8c2c32ce1108` |
| `automation/source/config/automation.example.json` | 51 | `e36f8c8476d6edab559ac8ca7eff25038d4d2a5900a53df1e83f3b8f97117b48` |
| `automation/source/config/trust/publishers.example.json` | 15 | `cdad5c766a6552ed37975e83ebfb27a61b3ac7bb75df620a03a839b201a7652f` |
| `automation/source/README.md` | 124 | `dfa96841e354272f0956833e7bb59702dfa107f5b0efa392096db58b17c523fb` |
| `automation/source/.gitignore` | 7 | `c452103ded1aa076061bc1f9b382bd4043954c73ffd213542c4c3f0ca243e4fc` |

## 说明

- 快照经  + "executor/redact.py" +  规则扫描：0 命中。
- 测试里的假 UDID / 手机号 / 个人路径样例按片段拼接生成，快照里没有可直接命中的字面量。
