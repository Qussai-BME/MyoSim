from pathlib import Path

import pytest

from myosim.core.types import IntentEvent, IntentLabel, IntentRecord
from myosim.experiments.provenance import (
    create_provenance,
    discover_git_commit,
    input_metadata,
    runtime_environment,
)


def make_record(
    *,
    protocol_id: str = "csv-intent-replay-v1",
    input_sha256: object = "a" * 64,
) -> IntentRecord:
    return IntentRecord(
        timestamp_s=0.0,
        intent_id="REST",
        confidence=0.99,
        modality="replay",
        source="csv-replay:example.csv",
        model_version="decoder-v1",
        protocol_id=protocol_id,
        run_id="run-0001",
        provenance={"input_sha256": input_sha256},
    )


def test_input_metadata_handles_synthetic_and_canonical_records() -> None:
    assert input_metadata((IntentEvent(0.0, IntentLabel.REST, 1.0),)) == (
        "synthetic-intent-event-v1",
        None,
    )
    assert input_metadata((make_record(),)) == ("csv-intent-replay-v1", "a" * 64)


@pytest.mark.parametrize(
    "records, match",
    [
        ((make_record(protocol_id="first"), make_record(protocol_id="second")), "protocol_id"),
        ((make_record(input_sha256="a" * 64), make_record(input_sha256="b" * 64)), "input_sha256"),
        ((make_record(input_sha256=7),), "input_sha256"),
        ((make_record(input_sha256={"malformed": "hash"}),), "input_sha256"),
    ],
)
def test_input_metadata_rejects_mixed_or_invalid_record_identities(
    records: tuple[IntentRecord, ...],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        input_metadata(records)


def test_create_provenance_validates_hash_and_captures_environment(tmp_path: Path) -> None:
    provenance = create_provenance(
        config_hash="c" * 64,
        physics_backend="mujoco",
        model_path=tmp_path / "hand.xml",
        model_version="model-v1",
        intent_source="synthetic",
        seed=17,
        task="test",
        package_version="0.1.3",
        repository_root=tmp_path,
        intent_protocol_id="synthetic-v1",
        environment={"python_version": "test"},
    )

    assert provenance.git_commit == "unavailable"
    assert provenance.environment == {"python_version": "test"}
    assert provenance.to_dict()["environment"] == {"python_version": "test"}
    assert set(runtime_environment()) >= {"python_version", "platform", "system"}
    with pytest.raises(ValueError, match="protocol"):
        create_provenance(
            config_hash="c" * 64,
            physics_backend="mujoco",
            model_path=tmp_path / "hand.xml",
            model_version="model-v1",
            intent_source="synthetic",
            seed=17,
            task="test",
            package_version="0.1.3",
            repository_root=tmp_path,
            intent_protocol_id="",
        )
    with pytest.raises(ValueError, match="SHA-256"):
        create_provenance(
            config_hash="c" * 64,
            physics_backend="mujoco",
            model_path=tmp_path / "hand.xml",
            model_version="model-v1",
            intent_source="synthetic",
            seed=17,
            task="test",
            package_version="0.1.3",
            repository_root=tmp_path,
            input_file_sha256="short",
        )


def test_discover_git_commit_returns_unavailable_outside_a_repository(tmp_path: Path) -> None:
    assert discover_git_commit(tmp_path) == "unavailable"
