"""Parse .env files and small git-related helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

ENV_FILE_CANDIDATES = (
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    ".env",
)

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_GITIGNORE_ENV_PATTERNS = {".env", ".env*", "*.env", "/.env", ".env.*", "**/.env"}


def find_env_file(root: Path) -> Optional[Path]:
    """Return the first conventional env file found in *root*, if any."""
    for name in ENV_FILE_CANDIDATES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a .env-style file into {KEY: value}.

    Tolerant on purpose: comments, blank lines, `export` prefixes and lines
    without `=` are skipped instead of raising.
    """
    keys: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not _KEY_RE.match(key):
            continue
        keys[key] = value.strip().strip('"').strip("'")
    return keys


def env_is_gitignored(root: Path) -> bool:
    """True when the project's .gitignore excludes .env files."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return False
    for raw in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line in _GITIGNORE_ENV_PATTERNS:
            return True
    return False
