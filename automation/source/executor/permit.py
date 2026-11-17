"""本机许可。云端任务和清单不能给自己授权。

许可文件在 automation/config/permits.json，不进发布清单。
每条 grant 写明 task_id、revision、scopes、budget、deadline。
saved_login 必须为 false：持续入口不复用已保存登录。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .common import TZ_HK
from .ledger import Ledger, attempt_key
from .manifest import TaskEntry

SCHEMA = "ioswb-local-permit/1"


@dataclass
class Grant:
    task_id: str
    revision: int
    scopes: tuple[str, ...]
    budget: int
    deadline: datetime


@dataclass
class PermitSet:
    saved_login: bool
    grants: list[Grant]
    blocked: str | None = None

    def allows(self, entry: TaskEntry, ledger: Ledger, now: datetime | None = None) -> tuple[bool, str]:
        if self.blocked:
            return False, self.blocked
        now = now or datetime.now(timezone.utc)
        matches = [g for g in self.grants
                   if g.task_id == entry.task_id and g.revision == entry.revision]
        if not matches:
            return False, "本机许可没有列出 %s" % entry.key
        grant = matches[0]
        if now > grant.deadline:
            return False, "许可已过期"
        extra = [s for s in entry.scopes if s not in grant.scopes]
        if extra:
            return False, "超出本机许可范围: %s" % ", ".join(extra)
        key = attempt_key(entry.task_id, entry.revision)
        used = ledger.events_for(key).count("claim")
        if used >= grant.budget:
            return False, "许可预算已用完"
        return True, ""


def _parse_deadline(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ_HK)
    return parsed.astimezone(timezone.utc)


def load_permits(path: Path) -> PermitSet:
    if not path.exists():
        return PermitSet(False, [], blocked="本机许可文件不存在，停止派发")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return PermitSet(False, [], blocked="本机许可文件不可读: %s" % exc)
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return PermitSet(False, [], blocked="本机许可 schema 不正确")
    if payload.get("saved_login") is True:
        return PermitSet(True, [], blocked="持续入口不使用已保存登录")
    raw_grants = payload.get("grants")
    if not isinstance(raw_grants, list):
        return PermitSet(False, [], blocked="grants 必须是数组")
    grants: list[Grant] = []
    seen: set[tuple[str, int]] = set()
    for index, raw in enumerate(raw_grants):
        if not isinstance(raw, dict):
            return PermitSet(False, [], blocked="grants[%d] 不是对象" % index)
        task_id = raw.get("task_id")
        revision = raw.get("revision")
        scopes = raw.get("scopes")
        budget = raw.get("budget")
        deadline = raw.get("deadline")
        if not isinstance(task_id, str) or not isinstance(revision, int):
            return PermitSet(False, [], blocked="grants[%d] 的任务编号不完整" % index)
        if (task_id, revision) in seen:
            return PermitSet(False, [], blocked="重复的本机许可 %s@r%d" % (task_id, revision))
        seen.add((task_id, revision))
        if not isinstance(scopes, list) or not scopes or not all(isinstance(s, str) and s for s in scopes):
            return PermitSet(False, [], blocked="%s 的 scopes 不完整" % task_id)
        if not isinstance(budget, int) or budget < 1:
            return PermitSet(False, [], blocked="%s 的 budget 必须是正整数" % task_id)
        if not isinstance(deadline, str):
            return PermitSet(False, [], blocked="%s 缺少 deadline" % task_id)
        try:
            parsed = _parse_deadline(deadline)
        except ValueError:
            return PermitSet(False, [], blocked="%s 的 deadline 无法解析" % task_id)
        grants.append(Grant(task_id, revision, tuple(scopes), budget, parsed))
    if not grants:
        return PermitSet(False, [], blocked="本机许可为空，停止派发")
    return PermitSet(False, grants, blocked=None)
