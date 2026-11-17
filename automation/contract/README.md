# 清单契约（从本机 parser 只读提取）

本目录不是已发布清单。`manifest/releases.json` 尚未发布，worker 不会读取本目录里的任何文件。
这里只是把本机现有实现实际接受的字段结构写清楚，供 01 以后照它发布清单。

- 提取时间：2026-11-17
- 提取方式：只读本机源码与 README，未运行 headless、未连接设备
- 依据文件：
  - `automation/executor/manifest.py` —— `parse_manifest()`（L57-L125）、`verify_task_binding()`（L128-L142）
  - `automation/executor/common.py` —— `SCHEMA_MANIFEST`（L16）、`TASK_ID_RE`（L39）、`SHA40_RE`（L40）、`SHA64_RE`（L41）
  - `automation/README.md` —— 第 3 节「发布清单协议」（L48-L81）

## 1. 结构

```json
{
  "schema": "ioswb-release-manifest/1",
  "protocol_version": 1,
  "generated_at": "<可选，字符串>",
  "tasks": [ { ...task... } ]
}
```

- `tasks` 每个元素是一个任务对象；同一 `(task_id, revision)` 出现两次会被拒（`manifest.py` L84-L87）。
- 未知字段被忽略（parser 不拒绝额外键），但只有下列字段会被读取。

## 2. 字段与约束

| 字段 | 必填 | parser 实际约束（行号） | `README.md` 是否写明 |
| --- | --- | --- | --- |
| `schema` | 是 | 必须等于 `ioswb-release-manifest/1`（L64-L65；`common.py` L16） | 是（示例里有） |
| `protocol_version` | 是 | 整数且 `>= 1`（L66-L68） | 是（示例里，未写约束） |
| `tasks` | 是 | 必须是数组（L69-L70） | 是 |
| `generated_at` | 否 | 只当字符串保存（L120-L123） | 是（示例里，未写可选性） |
| `task_id` | 是 | 匹配 `^[A-Z][A-Z0-9]{1,11}-\d{3}$`（L79；`common.py` L39） | 否（只给示例值） |
| `revision` | 是 | 整数且 `>= 1`（L80-L83） | 是（示例里，未写约束） |
| `status` | 是 | 枚举 `published` / `withdrawn` / `draft`（L26、L88-L90） | 部分（正文写了只有 published 会被领取） |
| `task_path` | 是 | 仓库内相对路径，禁止绝对路径与 `..`，必须以 `.md` 结尾（L92-L96；`safe_relpath`） | 否 |
| `task_commit` | 是 | 40 位小写十六进制（L97-L99；`common.py` L40），且必须是分支 HEAD 的祖先（L130-L132） | 部分（写了祖先校验，未写大小写） |
| `content_sha256` | 是 | 64 位小写十六进制（L100-L102；`common.py` L41），必须等于 `git show <task_commit>:<task_path>` 的字节 sha256（L134-L142） | 是（L62、L75） |
| `scopes` | 是 | 非空字符串数组（L103-L105） | 是（示例里，未写「非空」） |
| `title` | 否 | 字符串，仅用于提交信息 | 是（示例里） |
| `meta` | 否 | 对象；仅 mock 模式读取 `meta.mock_harness`，live 忽略 | 否 |

**README 未写、以 parser 为准的约束**：`task_id` 正则、`task_path` 的 `.md` 与反逃逸、`revision` 下界、
`scopes` 非空、重复 `(task_id, revision)` 拒绝。README 的字段名与 parser 一致，没有名实不符的字段。

## 3. 内容摘要 ≠ git blob SHA

协议允许「该任务文件的 git blob SHA」或「与该 blob 绑定的 content hash」。本机实现取后者：

- `content_sha256 = sha256(<git show <task_commit>:<task_path> 的字节>)`
- 它与 `git rev-parse <task_commit>:<task_path>` 得到的 blob SHA-1 **不是同一个值**。
- 两者都绑定到同一个 commit 与 blob；worker 只接受 `content_sha256` 这种形式。

如果 01 希望清单里直接写 git blob SHA，需要扩展 parser；当前实现不支持。

## 4. 与协议文档的一处路径差异

- `docs/AUTOMATION_PROTOCOL.md` L28：`results/<task_id>/<revision>/a<n>.md`
- `tasks/IOS-002.md` 交付物：`results/IOS-002/r1/a1.md`
- 本机实现：`results/<task_id>/r<revision>/a<n>.md`（`config.result_rel_path`），与本单交付物一致。

即：具体任务单用 `r1`，协议里的 `<revision>` 占位符未写 `r` 前缀。本单按交付物执行；建议 01 在协议里
把占位符改成 `r<revision>` 或在清单里说明。

## 5. 信任绑定（与清单字段相关）

- `pinned_manifest_sha256` 现支持两种写法：`<sha256>`（裸摘要）与 `<sha256>:<commit>`（摘要 + 提交绑定）。
- 裸摘要**只有在清单提交同时出现在 `pinned_commit` 里**才成立；否则拒绝，并给出「未绑定到具体 commit」原因。
- 绑定的 commit 是「最后一次修改清单文件的提交」（`git rev-list -1 <head> -- manifest/releases.json`），
  不是分支 HEAD —— 否则任何后续提交（包括回执提交）都会让已钉的摘要失效。
