from __future__ import annotations

from pathlib import Path

from src.cloud_reasoner_client import validate_against_schema
from src.cloud_reasoner_mock import build_cloud_skill_response, build_local_reasoner_response, validate_authorized_he_ops
from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_reasoner_outputs_match_schema(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    request = {
        "sample_id": payload.sample_id,
        "session_id": payload.session_id,
        "sanitized_text": payload.sanitized_text,
        "metadata": payload.metadata,
        "policy_summary": payload.policy_summary,
        "public_context": payload.public_context,
    }
    local_response = build_local_reasoner_response(request)
    cloud_response = build_cloud_skill_response(request)
    schema_root = Path(__file__).resolve().parent.parent / "skills" / "privacy_expense_cloud_reasoner" / "schemas"
    assert validate_against_schema(local_response, schema_root / "cloud_reasoner_response.schema.json")["valid"] is True
    assert validate_against_schema(cloud_response, schema_root / "he_call_plan.schema.json")["valid"] is True
    assert validate_authorized_he_ops(cloud_response, payload.metadata)["authorized"] is True

