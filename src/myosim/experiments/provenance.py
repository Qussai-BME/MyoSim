"""Run identity and provenance records for deterministic experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, check_output
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """Machine-readable identity of one MyoSim execution."""

    run_id: str
    created_at_utc: str
    config_hash: str
    git_commit: str
    physics_backend: str
    model_path: str
    model_version: str
    intent_source: str
    seed: int
    task: str
    package_version: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def discover_git_commit(repository_root: Path) -> str:
    """Return the current commit without failing a detached source distribution."""
    try:
        return check_output(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            text=True,
            stderr=DEVNULL,
        ).strip()
    except (CalledProcessError, FileNotFoundError):
        return "unavailable"


def create_provenance(
    *,
    config_hash: str,
    physics_backend: str,
    model_path: Path,
    model_version: str,
    intent_source: str,
    seed: int,
    task: str,
    package_version: str,
    repository_root: Path,
) -> RunProvenance:
    """Create provenance once at the beginning of an experiment."""
    return RunProvenance(
        run_id=uuid4().hex,
        created_at_utc=datetime.now(UTC).replace(microsecond=0).isoformat(),
        config_hash=config_hash,
        git_commit=discover_git_commit(repository_root),
        physics_backend=physics_backend,
        model_path=str(model_path),
        model_version=model_version,
        intent_source=intent_source,
        seed=seed,
        task=task,
        package_version=package_version,
    )
