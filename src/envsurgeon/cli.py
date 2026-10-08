"""envsurgeon CLI — zero dependencies, Python 3.9+."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .report import Style, color_enabled

EXIT_OK = 0
EXIT_FINDINGS = 1


def _cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2
    return run_doctor(
        root,
        json_output=args.json,
        strict=args.strict,
        quiet=args.quiet,
    )


def _cmd_scan(args: argparse.Namespace) -> int:
    from .leak import scan_for_leaks
    from .report import Style, color_enabled

    root = Path(args.path).resolve()
    style = Style(False if args.json else color_enabled())
    findings = scan_for_leaks(root)
    if args.json:
        import json

        print(json.dumps([f.__dict__ for f in findings], indent=2))
        return EXIT_FINDINGS if findings else EXIT_OK
    if not findings:
        print(style.green("✔ no hardcoded secrets detected"))
        return EXIT_OK
    print(style.red(f"✘ {len(findings)} potential secret leak(s) found"))
    for f in findings:
        print(f"  {style.bold(f.kind)}  {f.file}:{f.line}  {style.dim(f.preview)}")
    print()
    print(style.dim("values are masked · rotate any key that was ever committed"))
    return EXIT_FINDINGS


def _cmd_usage(args: argparse.Namespace) -> int:
    from .usage import scan_code
    from .report import Style, color_enabled

    root = Path(args.path).resolve()
    style = Style(False if args.json else color_enabled())
    usage = scan_code(root)
    if args.json:
        import json

        print(json.dumps({k: v for k, v in sorted(usage.items())}, indent=2))
        return EXIT_OK
    if not usage:
        print(style.yellow("! no environment variable usage found"))
        return EXIT_OK
    for key in sorted(usage):
        locs = usage[key]
        first = f"{locs[0][0]}:{locs[0][1]}"
        extra = f" (+{len(locs) - 1} more)" if len(locs) > 1 else ""
        print(f"{style.cyan(key)}  {style.dim(first + extra)}")
    print()
    print(style.dim(f"{len(usage)} variable(s) read by code"))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envsurgeon",
        description="Diagnose missing, unused, and leaked environment variables.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser(
        "doctor",
        help="full diagnosis: missing, unused, leaked, gitignore",
    )
    p_doc.add_argument("path", nargs="?", default=".", help="project root (default: .)")
    p_doc.add_argument("--json", action="store_true", help="machine-readable output")
    p_doc.add_argument(
        "--strict", action="store_true",
        help="also fail on warnings (unused vars, secrets, missing .gitignore)",
    )
    p_doc.add_argument("--quiet", action="store_true", help="only print the verdict line")
    p_doc.set_defaults(func=_cmd_doctor)

    p_scan = sub.add_parser("scan", help="only scan for hardcoded secrets")
    p_scan.add_argument("path", nargs="?", default=".")
    p_scan.add_argument("--json", action="store_true")
    p_scan.set_defaults(func=_cmd_scan)

    p_use = sub.add_parser("usage", help="list env vars read by code, with locations")
    p_use.add_argument("path", nargs="?", default=".")
    p_use.add_argument("--json", action="store_true")
    p_use.set_defaults(func=_cmd_usage)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
