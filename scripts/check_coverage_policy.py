"""Fail a release check when any substantive MyoSim source module misses coverage policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MINIMUM_STATEMENTS = 10


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print("usage: check_coverage_policy.py COVERAGE_JSON MINIMUM_PERCENT", file=sys.stderr)
        return 2
    path = Path(args[0])
    minimum = float(args[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for filename, details in sorted(data["files"].items()):
        summary = details["summary"]
        statements = int(summary["num_statements"])
        if statements < MINIMUM_STATEMENTS:
            continue
        percent = float(summary["percent_covered"])
        if percent < minimum:
            failures.append(f"{filename}: {percent:.2f}% < {minimum:.2f}%")
    if failures:
        print("Per-module coverage policy failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Per-module coverage policy passed: every substantive module is >= {minimum:.2f}%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
