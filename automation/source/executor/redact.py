"""回执脱敏闸门。

入库前对“即将写进公开仓库的那一份字节”做一次硬扫描：
命中任何一条规则就拒绝上传（标记 quarantined），只在本机保留隔离副本。

这不是内容审核，而是防止截图路径以外的敏感值、凭据、完整设备 ID 或个人路径
被自动流程带进公开仓库。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_BUSINESS_DIR = "D:\\GoDemo\\wbjiaoben"


def _normalize_path(value: str) -> str:
    """统一分隔符，并把源码里转义的双反斜杠折叠成单反斜杠。"""
    text = value.replace("/", "\\")
    while "\\\\" in text:
        text = text.replace("\\\\", "\\")
    return text.lower()


@dataclass
class Finding:
    rule: str
    line: int
    sample: str

    def as_dict(self) -> dict:
        return {"rule": self.rule, "line": self.line, "sample": self.sample}


def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 6:
        return "***"
    return value[:4] + "***" + value[-2:]


_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Apple 设备 UDID 形态（8-16 位十六进制）
    ("device_udid", re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}\b")),
    # 中国大陆手机号
    ("phone_number", re.compile(r"(?<![0-9A-Fa-f])1[3-9]\d{9}(?![0-9A-Fa-f])")),
    # 用户主目录
    ("personal_home", re.compile(r"(?i)\b[A-Z]:\\\\?Users\b|/(?:home|Users)/[A-Za-z0-9._-]+")),
    # 私钥
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    # 常见令牌前缀
    ("token_prefix", re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})\b")),
    # 账号参数赋值（只在出现“看起来像值”的时候才拦）
    ("account_param", re.compile(
        r"(?i)\b(?:usergsid|useruid|gsid|cookie|access_token|refresh_token|api[_-]?key|secret)\b\s*[:=]\s*[\"']?[A-Za-z0-9%._~+/=-]{8,}"
    )),
    # 设备 ID 形式的十六进制串（排除标准摘要长度：40=sha1/commit，64=sha256）
    ("opaque_hex", re.compile(r"\b[0-9a-f]{48,}\b")),
    # 超长 base64 块（截图/附件）
    ("base64_blob", re.compile(r"[A-Za-z0-9+/]{240,}={0,2}")),
]


def scan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        for rule, pattern in _PATTERNS:
            for match in pattern.finditer(line):
                token = match.group(0)
                if rule == "opaque_hex" and len(token) in (40, 64):
                    # 40 位 = git commit/sha1，64 位 = sha256；公开回执允许写完整摘要
                    continue
                findings.append(Finding(rule=rule, line=number, sample=_mask(token)))
        # 绝对路径：业务目录以外一律拦（明确允许业务目录本身作为“业务目录”出现）
        for match in re.finditer(r"(?<![A-Za-z])[A-Za-z]:\\\\?[^\s\"'<>|]{2,}", line):
            token = match.group(0)
            normalized = _normalize_path(token)
            if normalized.startswith(_normalize_path(ALLOWED_BUSINESS_DIR)):
                continue
            findings.append(Finding(rule="foreign_abs_path", line=number, sample=_mask(token)))
    return findings


def is_clean(text: str) -> bool:
    return not scan(text)
