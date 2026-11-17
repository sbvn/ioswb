"""IOSWB 自动任务执行器（本地框架）。

模块：
- config    配置与模式闸门
- locking   操作系统排他锁
- ledger    持久化台账
- gitrepo   Git 读写（正常认证、不强推）
- manifest  机器可读发布清单与内容绑定
- trust     发布身份信任规则
- redact    回执脱敏闸门
- runner    执行适配器（mock / dsh headless）
- worker    单 worker / 单任务状态机
- control   操作员控制面
"""

__all__ = ["config", "control", "gitrepo", "ledger", "locking", "manifest",
           "redact", "runner", "trust", "worker"]
__version__ = "0.1.0"
