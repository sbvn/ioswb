# BOOTSTRAP 限定验收

- 对象：`automation/BOOTSTRAP.md`
- 回执提交：[`d6a0c8cc88ec52caf02543e41095ed30e3180f86`](https://github.com/sbvn/ioswb/commit/d6a0c8cc88ec52caf02543e41095ed30e3180f86)
- 父提交：`3641d2ff8c9a5c7c65248ed22070394c48df15f5`
- 终审：01
- 终审日期（Asia/Hong_Kong）：2026-11-17
- 目标仓库：https://github.com/sbvn/ioswb
- 读取 ref：`cursor/init-collab-docs-2e45`

本文件受理这份回执。它不在 `results/` 下，但是用户对 t109 的直接指令回执，按兼容例外接受。不要求重做，也不要求搬迁路径。本验收不扩大执行许可。

## 结论

限定验收：离线框架的 mock 成果可以进入下一阶段，也就是协议对齐。

不能判定为失败，也不能判定为全部通过。仓库里只有这份报告，没有实现代码，不能确认框架已经可靠实现。执行方自述不升格为团队独立验证。

## 团队独立核到的事实

- 该提交只新增 `automation/BOOTSTRAP.md`，257 行。
- 本分支没有 `manifest/releases.json`，没有 `automation/` 下的实现源码。
- 公开提交的 `%G?` 显示为 `N`。本环境没有配置 SSH allowed signers，因此这只说明这些提交没有可用的已验证签名，不能当成完成了签名审计。

## 执行方自述（不升格）

下列内容只来自回执正文。团队没有运行测试，没有查看本机 24 个文件，也没有执行 `dsh`。

- 本机 `D:\GoDemo\wbjiaoben\automation\` 新增 24 个框架文件。
- 离线 mock 19/19 通过。
- mock worker 曾常驻；回执写明它可能随会话回收。真实 live 没有启动。
- 信任规则 allow 为空，清单未发布。live 因此被阻塞。
- 本机 `@deepseek-ai/dsh` 自述为 `0.2.2-rc.3`。`--help`、`--version` 和安装包内文档有 headless 入口。`dsh --profile headless` 的模型端到端没有跑。

入口文档或启动器存在，不等于这条调用真实可用。

## 必须收住的口径

- `test_business_files_untouched` 在回执里的验证点是「既有业务脚本仍在、未被删除」。这只说明报告声称检查了存在，不等于哈希未改。团队也没看到该测试源码。
- 发布者签名未配置。不能把未签名提交当成已验签。
- 信任规则是摘要钉、提交钉、签名指纹三选一。摘要钉必须和具体 commit 的语义绑在一起，不能只因内容相似就放行。本验收不批准生产信任锚。
- STOP 三个时点和崩溃后的 `recovery_required` 目前只有自述。不能只看自述就当成边界已经成立。
- live 阻塞照实保留：信任为空，且本分支没有已发布清单。这不是失败结论，也不是 live 已通过。

## 效力

可以据此发布下一份框架任务。手机、Frida、注册、凭据、headless 模型调用、安装服务、降低审批、启用 live、配置生产信任锚，仍然没有授权。
