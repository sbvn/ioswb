# 框架源码快照（离线持续调度）

- 来源：公开快照，加上云端这一轮的调度改动
- 快照时间（Asia/Hong_Kong）：2026-11-17
- 用途：本机以后按固定提交自行核对。云端没有部署，也没有调用模型
- 真实 `manifest/releases.json`、旧任务和旧回执没有改

## 已排除

- `config/automation.json` 与 `config/trust/publishers.json`（真实配置值与受限信任锚）
- `state/`、`outbox/`、`mocklab/`、`tests/.work/`（运行产物）

## 本轮变化

- `bin/dsh_loop.py`：单进程持续入口。磁盘保持 dry-run。只有同时给出 `--dispatch` 和 `--offline-run` 才在内存 overlay 里用 fake runner。不调用真实模型，不加载已保存登录。
- `executor/permit.py`：本机 `config/permits.json` 写明任务、版本、范围、预算、期限。过期、超范围、预算用完或 `saved_login=true` 都不领取。
- `executor/overlay.py`：临时 patch 在 `finally` 删除。配置字节若被改写会还原。下次启动先清残留。
- `executor/ledger.py`：台账末尾半行或坏 JSON 时拒绝启动，不再丢掉坏行后继续领取。
- `executor/worker.py`：原始回执和 `.meta.json` 分路径上传。补传不重新执行。
- `executor/runner.py`：fake runner 也要求退出码 0 且 `final.reason.kind` 为 `completed`。`command` / `args` 不进入子进程。

全量 `run_tests.py`：46 通过，2 跳过（快照目录不是业务树），0 失败，340.6 秒。演示命令是 `python3 automation/source/tests/demo_continuous.py`。这是实现方自测，不是独立验收。

## 本机以后自行核对

本轮没有替本机覆盖文件。`executor/handoff.py` 未改，仍是 `9eb7690ddaadb4b4e9dea36b80c66c83d76e61e4f18741b3bfbae543f6733484`。

`executor/runner.py` 的上一版是 `674535cac88c91bd1f41d0d27449e76b08df1bf584d7c9d7bd3cf46a58b41b56`，这一版是 `b016bee52197ca80c51492c3020213e1b9ff3a745eebf94152af80097b5aedab`。本机文件若两者都不是，停止，不要覆盖。下表是当前快照。

## 文件与哈希

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| `automation/source/executor/__init__.py` | 18 | `baa7c09c1efc7ac6753a669a6df996d670bfcc3134731bbdbc408cd58d871f33` |
| `automation/source/executor/common.py` | 164 | `a1826e6b2db2382d99c21556e835c6aafd96611564f1ad6fa9086e989a99c7a7` |
| `automation/source/executor/config.py` | 307 | `df0c04ef2f7bcf251f2d328989e2c59b9b5ba6954b24d02abc608af2f11397c6` |
| `automation/source/executor/control.py` | 112 | `6a6cd7b37eb82c207eb39fb5a1fb667cb748bd3bc611f622585f072c0d7f2b1f` |
| `automation/source/executor/gitrepo.py` | 181 | `d6d1f76fe6a37c23bda2ed73d0d01daf0e9ec64f6d09c5b4249a6346bd648658` |
| `automation/source/executor/handoff.py` | 129 | `9eb7690ddaadb4b4e9dea36b80c66c83d76e61e4f18741b3bfbae543f6733484` |
| `automation/source/executor/ledger.py` | 218 | `fbb238283066623b619222aca07cfdaade9411e2cdba8d96c21ab9856a2e63ef` |
| `automation/source/executor/locking.py` | 77 | `10afffc2e429f38d27a19c668e47d06f16b7de80326b2dce6ffbc516c5a97e9b` |
| `automation/source/executor/manifest.py` | 143 | `b7a625b85b4b629fcb509132d47d47a9f6937836cea12199900e88504c6b7515` |
| `automation/source/executor/overlay.py` | 80 | `402bc41796e4fba2d0af567ddf32ff3be3b771213e82a8f9ac8488808c7f1245` |
| `automation/source/executor/permit.py` | 109 | `c0bfae2bfd474c9cd6d39aab7fbfef2c9adb794c33b15d1a5d53553c4ee32042` |
| `automation/source/executor/redact.py` | 85 | `dad425e60fdc0dd327b8c803e0582c0c80dfb383ce24c457ec0ed71b48644c89` |
| `automation/source/executor/runner.py` | 432 | `b016bee52197ca80c51492c3020213e1b9ff3a745eebf94152af80097b5aedab` |
| `automation/source/executor/sigverify.py` | 170 | `af4b48596a7174a1c8c451230002880d93e037102572def0c50825adc2b22d0c` |
| `automation/source/executor/trust.py` | 199 | `61225c6d9dc3d998b072dba71766fec3d7429d203c46862f4a4a748faf3bed92` |
| `automation/source/executor/worker.py` | 762 | `8eca49033bce6ab7d8fe885a8eb65d97306c13bffc94270692f57c5ed395dcbb` |
| `automation/source/bin/dsh_loop.py` | 78 | `c9c6a8cb85a8209e4222e3807c7ce25fb3d5b41b526ae16d0ea31511d6563d93` |
| `automation/source/bin/dsh_worker.py` | 62 | `44d3ee169472ab465e2667c43a72fafdafdeea0727f710d517a286ed24b9fff4` |
| `automation/source/bin/dsh_control.py` | 58 | `f595d8464337a439b9df6c62b8e86d4b5c468b150d9543422aa3f961624c5832` |
| `automation/source/bin/setup_mock_lab.py` | 175 | `0f4e9d1a2329d74a8c6d0bc5d558747acd7bf83da5be1dd4c0a86b2b0676f989` |
| `automation/source/bin/connect_wait.py` | 319 | `baf5cc6410c9438f6246583b19268a91749e14ee41134eb1528fa58813d0a399` |
| `automation/source/tests/lab.py` | 383 | `48d3c527184b75e604616f7e09188ff83b223800121a990fef8963a088dced72` |
| `automation/source/tests/run_tests.py` | 1144 | `b0d5186263e8b84fc0c140f22e87f00bb412cdaa4187ec0d8a5fd9653b6d8aec` |
| `automation/source/tests/demo_continuous.py` | 192 | `d89ad6251a55b341d0bdf94587664d11b5db29081a1820316e8f91d03db8ec89` |
| `automation/source/tests/probe_final_gate.py` | 220 | `5aaf2af0def91ad6929bc7f1ff8d0f6d8a55a9ec836a1d92442982469efec2d9` |
| `automation/source/tests/fake_harness.py` | 109 | `8d463f8ca9e3c6d0cccfb40c9fe91a888fa1c5081a6139344ad2c66c486c0df7` |
| `automation/source/config/automation.example.json` | 51 | `e36f8c8476d6edab559ac8ca7eff25038d4d2a5900a53df1e83f3b8f97117b48` |
| `automation/source/config/trust/publishers.example.json` | 15 | `cdad5c766a6552ed37975e83ebfb27a61b3ac7bb75df620a03a839b201a7652f` |
| `automation/source/README.md` | 218 | `19c9f548c7b402a0a8f42c0fd059f65a830316ee189870370ed4821d3c470a52` |
| `automation/source/LOOP.md` | 27 | `bd1cf605c6b33da284d0a7b9f71ed491c9169ec19ed413deaf7338903edbb311` |
| `automation/source/.gitignore` | 8 | `c452103ded1aa076061bc1f9b382bd4043954c73ffd213542c4c3f0ca243e4fc` |

## 说明

- 表内哈希是当前文件字节的 sha256，不是 git blob SHA-1。
- 快照经 `executor/redact.py` 规则扫描的对象仍是源码，不含密钥。
- 真实信任锚与本地登录配置都不在快照内。
