"""Detect hardcoded and committed secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .usage import iter_source_files

MAX_FILE_BYTES = 1_000_000


@dataclass
class Finding:
    kind: str
    file: str
    line: int
    preview: str


_RULES: List[Tuple[str, re.Pattern]] = [
    ("AWS Access Key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("GitHub Token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,255})\b")),
    ("Stripe Secret Key", re.compile(r"\b(sk_(?:live|test)_[0-9a-zA-Z]{16,})\b")),
    ("OpenAI API Key", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b")),
    ("Google API Key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")),
    ("Slack Token", re.compile(r"\b(xox[baprs]-[0-9A-Za-z-]{10,})\b")),
    ("Telegram Bot Token", re.compile(r"\b(\d{8,10}:[A-Za-z0-9_-]{35})\b")),
    ("Private Key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "JWT",
        re.compile(
            r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"
        ),
    ),
    (
        "Hardcoded secret",
        re.compile(
            r"""(?i)(?:api[_-]?key|apikey|secret|token|password|passwd|pwd|"""
            r"""access[_-]?key|auth[_-]?key)['"]?\s*[:=]\s*['"]"""
            r"""([A-Za-z0-9_\-+/=.]{16,})['"]"""
        ),
    ),
]

_PLACEHOLDER = re.compile(
    r"(?i)(your|example|sample|dummy|fake|placeholder|changeme|change_me|"
    r"redacted|todo|fixme|xxxxxxxx|<[^>]*>|\$\{|\{\{|process\.env|os\.environ)"
)


def _looks_like_placeholder(value: str) -> bool:
    if _PLACEHOLDER.search(value):
        return True
    if len(set(value)) < 5:
        return True
    if value.isupper() and "_" in value:  # e.g. API_KEY=API_KEY
        return True
    return False


def _mask(value: str) -> str:
    if len(value) <= 8:
        return value[:2] + "*" * max(len(value) - 2, 1)
    return value[:4] + "\u2026" + value[-4:]


def scan_for_leaks(root: Path) -> List[Finding]:
    """Scan files under *root* for secret-looking strings. Values are masked."""
    root = root.resolve()
    findings: List[Finding] = []
    for path in iter_source_files(root, include_env=True):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8192]:
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        text = data.decode("utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in _RULES:
                for match in pattern.finditer(line):
                    value = match.group(1) if match.groups() else match.group(0)
                    if kind == "Hardcoded secret" and _looks_like_placeholder(value):
                        continue
                    findings.append(Finding(kind, rel, lineno, _mask(value)))
    return findings
