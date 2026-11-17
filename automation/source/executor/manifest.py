"""机器可读发布清单（release manifest）。

本仓库目前还没有正式清单，本模块先定义执行器认可的协议并严格校验；
清单缺失即说明“发布协议未就绪”，执行器不得自行编造任务。

期望路径：<branch>:manifest/releases.json （可由配置改）
期望结构见 README「发布清单协议」。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .common import (
    SCHEMA_MANIFEST,
    SHA40_RE,
    SHA64_RE,
    TASK_ID_RE,
    ManifestError,
    read_json_bytes,
    safe_relpath,
    sha256_bytes,
)

STATUSES = ("published", "withdrawn", "draft")


@dataclass
class TaskEntry:
    task_id: str
    revision: int
    status: str
    task_path: str
    task_commit: str
    content_sha256: str
    scopes: tuple[str, ...]
    title: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return "%s@r%d" % (self.task_id, self.revision)


@dataclass
class Manifest:
    protocol_version: int
    tasks: list[TaskEntry]
    raw_sha256: str
    generated_at: str = ""

    def published(self) -> list[TaskEntry]:
        return [t for t in self.tasks if t.status == "published"]


def parse_manifest(data: bytes) -> Manifest:
    try:
        payload = read_json_bytes(data)
    except Exception as exc:  # noqa: BLE001
        raise ManifestError("清单不是合法 JSON: %s" % exc) from exc
    if not isinstance(payload, dict):
        raise ManifestError("清单根必须是对象")
    if payload.get("schema") != SCHEMA_MANIFEST:
        raise ManifestError("清单 schema 必须是 %s，实际 %r" % (SCHEMA_MANIFEST, payload.get("schema")))
    protocol_version = payload.get("protocol_version")
    if not isinstance(protocol_version, int) or protocol_version < 1:
        raise ManifestError("protocol_version 必须是 >=1 的整数")
    tasks_raw = payload.get("tasks")
    if not isinstance(tasks_raw, list):
        raise ManifestError("tasks 必须是数组")

    entries: list[TaskEntry] = []
    seen: set[tuple[str, int]] = set()
    for index, raw in enumerate(tasks_raw):
        if not isinstance(raw, dict):
            raise ManifestError("tasks[%d] 必须是对象" % index)
        task_id = raw.get("task_id")
        if not isinstance(task_id, str) or not re.match(TASK_ID_RE, task_id):
            raise ManifestError("tasks[%d].task_id 非法: %r" % (index, task_id))
        revision = raw.get("revision")
        if not isinstance(revision, int) or revision < 1:
            raise ManifestError("%s.revision 必须是 >=1 的整数" % task_id)
        key = (task_id, revision)
        if key in seen:
            raise ManifestError("重复的 %s@r%d" % key)
        seen.add(key)
        status = raw.get("status")
        if status not in STATUSES:
            raise ManifestError("%s.status 必须是 %s 之一" % (task_id, "/".join(STATUSES)))
        try:
            task_path = safe_relpath(raw.get("task_path") or "")
        except ValueError as exc:
            raise ManifestError("%s.task_path 非法: %s" % (task_id, exc)) from exc
        if not task_path.endswith(".md"):
            raise ManifestError("%s.task_path 必须是 .md" % task_id)
        task_commit = raw.get("task_commit")
        if not isinstance(task_commit, str) or not re.match(SHA40_RE, task_commit):
            raise ManifestError("%s.task_commit 必须是 40 位小写十六进制" % task_id)
        digest = raw.get("content_sha256")
        if not isinstance(digest, str) or not re.match(SHA64_RE, digest):
            raise ManifestError("%s.content_sha256 必须是 64 位小写十六进制" % task_id)
        scopes = raw.get("scopes")
        if not isinstance(scopes, list) or not all(isinstance(s, str) and s for s in scopes):
            raise ManifestError("%s.scopes 必须是非空字符串数组" % task_id)
        entries.append(
            TaskEntry(
                task_id=task_id,
                revision=revision,
                status=status,
                task_path=task_path,
                task_commit=task_commit,
                content_sha256=digest,
                scopes=tuple(scopes),
                title=str(raw.get("title") or ""),
                meta=raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
            )
        )

    return Manifest(
        protocol_version=protocol_version,
        tasks=entries,
        raw_sha256=sha256_bytes(data),
        generated_at=str(payload.get("generated_at") or ""),
    )


def verify_task_binding(entry: TaskEntry, repo, branch_head: str) -> tuple[bool, str, bytes]:
    """校验任务内容与清单声明一致：固定提交可读、摘要匹配、提交在分支祖先链上。"""
    if not repo.is_ancestor(entry.task_commit, branch_head):
        return False, "task_commit %s 不在分支 %s 的祖先链上" % (
            entry.task_commit[:8], "当前分支"
        ), b""
    try:
        data = repo.read_file(entry.task_commit, entry.task_path)
    except Exception as exc:  # noqa: BLE001
        return False, "无法读取 %s@%s: %s" % (entry.task_path, entry.task_commit[:8], exc), b""
    actual = sha256_bytes(data)
    if actual != entry.content_sha256:
        return False, "内容摘要不符（清单 %s / 实际 %s）" % (
            entry.content_sha256[:12], actual[:12]
        ), data
    return True, "", data
