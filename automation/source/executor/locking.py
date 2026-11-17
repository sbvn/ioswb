"""操作系统级排他锁。

约束（来自任务要求）：
- 单 worker、单任务；锁必须是操作系统排他锁，而不是“我看看心跳新不新”。
- 心跳过旧不允许抢锁重跑；holder 进程还活着时，第二个 worker 必须退出。
- 进程被强杀时由操作系统释放锁，这是唯一合法的“接管”方式。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    import msvcrt
else:
    import fcntl


class ProcessLock:
    """非阻塞排他锁。

    acquire() 返回 False 表示已有其他 worker 持有；调用方必须退出，不得等待或抢占。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            if _IS_WINDOWS:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, (json.dumps({"pid": os.getpid()}) + "\n").encode("utf-8")[:512])
        except OSError:
            pass
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if _IS_WINDOWS:
                os.lseek(self._fd, 0, os.SEEK_SET)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(self._fd)
        finally:
            self._fd = None


def lock_is_held(path: Path) -> bool:
    """只读嗅探：锁文件现在是否被别的进程持有。用于 status 展示，不用于接管。"""
    if not path.exists():
        return False
    probe = ProcessLock(path)
    if probe.acquire():
        probe.release()
        return False
    return True
