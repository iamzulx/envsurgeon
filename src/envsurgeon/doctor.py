"""The `doctor` command: run every check and print a single verdict."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

from .leak import scan_for_leaks
from .parsers import env_is_gitignored, find_env_file, parse_env_file
from .report import Style, color_enabled
from .usage import scan_code

EXIT_OK = 0
EXIT_FINDINGS = 1

IGNORED_KEYS = {
    "PATH", "HOME", "USER", "SHELL", "PWD", "TERM", "LANG", "LC_ALL",
    "CI", "TZ", "HOSTNAME", "EDITOR", "TMPDIR", "PYTHONPATH", "NODE_ENV",
}


def run_doctor(
    root: Path,
    json_output: bool = False,
    strict: bool = False,
    quiet: bool = False,
) -> int:
    style = Style(False if json_output else color_enabled())

    env_file = find_env_file(root)
    declared = parse_env_file(env_file) if env_file else {}
    usage = scan_code(root)
    leaks = scan_for_leaks(root)
    gitignored = env_is_gitignored(root)

    used_keys = {k for k in usage if k not in IGNORED_KEYS}
    missing = sorted(k for k in used_keys if k not in declared)
    unused = sorted(k for k in declared if k not in used_keys)

    problems = len(missing) + len(leaks)
    warnings = len(unused) + (0 if gitignored or not env_file else 1)

    result: Dict[str, object] = {
        "root": str(root),
        "env_file": str(env_file.relative_to(root)) if env_file else None,
        "declared_count": len(declared),
        "used_count": len(used_keys),
        "missing": missing,
        "unused": unused,
        "leaks": [f.__dict__ for f in leaks],
        "env_gitignored": gitignored,
        "ok": problems == 0 and (not strict or warnings == 0),
    }

    if json_output:
        print(json.dumps(result, indent=2))
        return EXIT_OK if result["ok"] else EXIT_FINDINGS

    if not quiet:
        if env_file:
            print(style.dim(f"scanning {root} · env file: {env_file.name}"))
        else:
            print(style.dim(f"scanning {root} · no .env file found"))
        print()

        if missing:
            print(style.red(f"✘ {len(missing)} variable(s) used but never declared"))
            for key in missing:
                loc = usage[key][0]
                print(f"    {style.bold(key)}  {style.dim(f'used at {loc[0]}:{loc[1]}')}")
            print(style.dim("  → add them to your env file, or new devs will hit a wall"))
            print()

        if leaks:
            print(style.red(f"✘ {len(leaks)} potential secret leak(s)"))
            for f in leaks:
                print(f"    {style.bold(f.kind)}  {f.file}:{f.line}  {style.dim(f.preview)}")
            print()

        if unused:
            print(style.yellow(f"! {len(unused)} variable(s) declared but never used"))
            for key in unused:
                print(f"    {style.bold(key)}")
            print()

        if env_file and not gitignored:
            print(style.yellow("! .env is not covered by .gitignore"))
            print(style.dim("  → add a `.env` line before you commit anything"))
            print()

        if not missing and not leaks and not unused:
            print(style.green("✔ no issues found — environment is in good shape"))
            print()

    verdict = (
        style.green("✔ healthy")
        if problems == 0 and warnings == 0
        else style.red(f"✘ {problems} problem(s), {warnings} warning(s)")
    )
    print(f"envsurgeon: {verdict}")

    if problems > 0:
        return EXIT_FINDINGS
    if strict and warnings > 0:
        return EXIT_FINDINGS
    return EXIT_OK


def run(argv: List[str] | None = None) -> int:  # pragma: no cover - convenience
    return run_doctor(Path.cwd(), json_output="--json" in (argv or sys.argv))
