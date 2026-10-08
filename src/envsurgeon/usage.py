"""Find which environment variables a codebase actually reads."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterator, List, Set, Tuple

SKIP_DIRS: Set[str] = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "dist",
    "build", "__pycache__", ".next", ".nuxt", ".svelte-kit", "target", "vendor",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
    ".idea", ".vscode", "coverage", ".turbo", "out", ".cache",
}

SCAN_EXTENSIONS: Set[str] = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rb", ".php",
    ".java", ".kt", ".cs", ".sh", ".bash", ".zsh", ".fish", ".yml", ".yaml",
    ".toml", ".tf", ".tfvars", ".conf", ".ini", ".cfg",
}

SCAN_FILENAMES: Set[str] = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile", "Procfile",
}

_PATTERNS: List[re.Pattern] = [
    # Python
    re.compile(r"""os\.environ(?:\.get)?\s*[\[(]\s*['"](\w+)['"]"""),
    re.compile(r"""os\.getenv\s*\(\s*['"](\w+)['"]"""),
    re.compile(r"""os\.environ\.setdefault\s*\(\s*['"](\w+)['"]"""),
    # JavaScript / TypeScript
    re.compile(r"""process\.env\.(\w+)"""),
    re.compile(r"""process\.env\s*\[\s*['"](\w+)['"]\s*\]"""),
    re.compile(r"""import\.meta\.env\.(\w+)"""),
    # Go
    re.compile(r"""os\.Getenv\s*\(\s*['"](\w+)['"]\s*\)"""),
    re.compile(r"""os\.LookupEnv\s*\(\s*['"](\w+)['"]\s*\)"""),
    # Ruby
    re.compile(r"""ENV\s*\[\s*['"](\w+)['"]\s*\]"""),
    re.compile(r"""ENV\.fetch\s*\(\s*['"](\w+)['"]"""),
    # PHP
    re.compile(r"""getenv\s*\(\s*['"](\w+)['"]\s*\)"""),
    re.compile(r"""\$_ENV\s*\[\s*['"](\w+)['"]\s*\]"""),
    # Shell / Docker / docker-compose / CI yaml: ${VAR} and ${VAR:-default}
    re.compile(r"""\$\{(\w+)(?::[-=?][^}]*)?\}"""),
]

Usage = Dict[str, List[Tuple[str, int]]]


def iter_source_files(root: Path, include_env: bool = False) -> Iterator[Path]:
    """Yield candidate source files under *root*, skipping vendor dirs."""
    root = root.resolve()
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if name in SCAN_FILENAMES or path.suffix in SCAN_EXTENSIONS:
                yield path
            elif include_env and (name == ".env" or name.startswith(".env.")):
                yield path


def scan_code(root: Path) -> Usage:
    """Return {ENV_VAR: [(relative_file, line_number), ...]} found in code."""
    root = root.resolve()
    usage: Usage = {}
    for path in iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pattern in _PATTERNS:
                for match in pattern.finditer(line):
                    key = match.group(1)
                    if not key or key[0].isdigit():
                        continue
                    locations = usage.setdefault(key, [])
                    loc = (rel, lineno)
                    if loc not in locations:
                        locations.append(loc)
    return usage
