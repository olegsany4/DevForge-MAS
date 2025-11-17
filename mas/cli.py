from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mas", description="DevForge-MAS CLI (bootstrap)")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("probe", help="run health probe").set_defaults(func=lambda _: (print("OK: mas cli probe"), 0)[1])
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    if ns.version:
        print("mas 0.1.0")
        return 0
    if hasattr(ns, "func"):
        return int(ns.func(ns) or 0)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
