"""Run identity and provenance records for deterministic experiments."""

from __future__ import annotations

import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, check_output
from uuid import uuid4

from myosim.core.types import IntentInput, IntentRecord


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """Machine-readable identity and environment record for one MyoSim execution."""

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
    intent_protocol_id: str = "not-applicable"
    input_file_sha256: str | None = None
    environment: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready snapshot with a copied environment mapping."""
        data = asdict(self)
        data["environment"] = dict(self.environment)
        return data


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


def input_metadata(inputs: Sequence[IntentInput]) -> tuple[str, str | None]:
    """Return the protocol and full file hash shared by one intent stream.

    Synthetic compatibility events have no input file. Canonical record streams
    must not mix protocol or source-file identities within one reproducible run.
    """
    records = tuple(item for item in inputs if isinstance(item, IntentRecord))
    if not records:
        return "synthetic-intent-event-v1", None
    protocol_ids = {record.protocol_id for record in records}
    input_hash_values = tuple(record.provenance.get("input_sha256") for record in records)
    if len(protocol_ids) != 1:
        raise ValueError("An experiment input stream must use one protocol_id")
    if any(value is not None and not isinstance(value, str) for value in input_hash_values):
        raise ValueError("IntentRecord input_sha256 provenance must be a string or null")
    input_hashes = set(input_hash_values)
    if len(input_hashes) != 1:
        raise ValueError("An experiment input stream must use one input_sha256 identity")
    input_hash = input_hashes.pop()
    if input_hash is not None and not isinstance(input_hash, str):
        raise ValueError("IntentRecord input_sha256 provenance must be a string or null")
    return protocol_ids.pop(), input_hash


def runtime_environment() -> dict[str, str]:
    """Capture stable, non-identifying environment facts relevant to reproduction."""
    return {
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "executable": sys.executable,
    }


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
    intent_protocol_id: str = "not-applicable",
    input_file_sha256: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> RunProvenance:
    """Create provenance once at the beginning of an experiment.

    ``input_file_sha256`` is nullable only for internally declared synthetic
    sources that have no input file. Artifact hashes are written separately in
    the immutable run-directory manifest after result files are created.
    """
    if not intent_protocol_id.strip():
        raise ValueError("intent_protocol_id must be non-empty")
    if input_file_sha256 is not None and len(input_file_sha256) != 64:
        raise ValueError("input_file_sha256 must be a SHA-256 hex digest when provided")
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
        intent_protocol_id=intent_protocol_id,
        input_file_sha256=input_file_sha256,
        environment=dict(environment) if environment is not None else runtime_environment(),
    )
