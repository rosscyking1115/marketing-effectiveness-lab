from __future__ import annotations

import json

import pytest

from marketing_effectiveness_lab.artifacts import (
    artifact_index_dataframe,
    load_artifact_index,
    persist_artifact,
    persist_json_artifact,
    read_artifact_text,
    verify_artifact_content,
)


def test_persist_artifact_writes_payload_and_index(tmp_path) -> None:
    record = persist_artifact(
        tmp_path,
        artifact_type="model_run_manifest",
        artifact_id="run_123",
        content="{\"run_id\":\"run_123\"}\n",
        content_type="application/json",
        file_extension="json",
        metadata={"source": "unit-test", "weekly_rows": 156},
        created_at_utc="2026-06-28T00:00:00Z",
    )

    records = load_artifact_index(tmp_path)
    index = artifact_index_dataframe(tmp_path)

    assert record.artifact_id == "run_123"
    assert record.content_path == "model_run_manifest/run_123.json"
    assert record.content_bytes == len(b'{"run_id":"run_123"}\n')
    assert read_artifact_text(tmp_path, record) == "{\"run_id\":\"run_123\"}\n"
    assert verify_artifact_content(tmp_path, record)
    assert records == [record]
    assert index.loc[0, "artifact_type"] == "model_run_manifest"
    assert index.loc[0, "metadata"]["weekly_rows"] == 156


def test_persist_json_artifact_uses_stable_serialization_and_content_id(tmp_path) -> None:
    payload = {"run_context": {"model": "MMM"}, "run_id": "abc"}

    record = persist_json_artifact(
        tmp_path,
        artifact_type="model_run_manifest",
        payload=payload,
        metadata={"kind": "demo"},
        created_at_utc="2026-06-28T00:00:00Z",
    )
    duplicate = persist_json_artifact(
        tmp_path,
        artifact_type="model_run_manifest",
        payload=payload,
        metadata={"kind": "demo-updated"},
        created_at_utc="2026-06-28T00:01:00Z",
    )

    records = load_artifact_index(tmp_path)
    parsed_payload = json.loads(read_artifact_text(tmp_path, record))

    assert record.artifact_id == duplicate.artifact_id
    assert record.content_sha256 == duplicate.content_sha256
    assert parsed_payload == payload
    assert len(records) == 1
    assert records[0].metadata == {"kind": "demo-updated"}


def test_artifact_index_can_filter_by_type(tmp_path) -> None:
    persist_artifact(
        tmp_path,
        artifact_type="model_run_manifest",
        artifact_id="run_1",
        content="{}",
        content_type="application/json",
        file_extension="json",
    )
    persist_artifact(
        tmp_path,
        artifact_type="crm_learning_library",
        artifact_id="learning_1",
        content="learning_dimension,learning_key\n",
        content_type="text/csv",
        file_extension="csv",
    )

    filtered = artifact_index_dataframe(tmp_path, artifact_type="crm_learning_library")

    assert filtered["artifact_id"].tolist() == ["learning_1"]


def test_artifact_registry_rejects_unsafe_identifiers(tmp_path) -> None:
    with pytest.raises(ValueError, match="artifact_id"):
        persist_artifact(
            tmp_path,
            artifact_type="model_run_manifest",
            artifact_id="../escape",
            content="{}",
            content_type="application/json",
            file_extension="json",
        )
