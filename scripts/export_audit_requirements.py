"""Write all declared MyoSim dependencies as a pip-audit requirements file."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def declared_requirements(pyproject_path: Path) -> tuple[str, ...]:
    """Return sorted, de-duplicated runtime and optional dependency specifiers."""
    payload: dict[str, Any] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = payload["project"]
    requirements = list(project["dependencies"])
    for group in project.get("optional-dependencies", {}).values():
        requirements.extend(group)
    return tuple(sorted(set(requirements), key=str.casefold))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Requirements-file path to write.",
    )
    args = parser.parse_args()
    args.output.write_text(
        "\n".join(declared_requirements(PROJECT_ROOT / "pyproject.toml")) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
