from __future__ import annotations

from pathlib import Path

from src.cloud_reasoner_client import validate_against_schema
from src.cloud_reasoner_mock import build_cloud_skill_response
from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_he_call_plan_schema_validation(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    plan = build_cloud_skill_response(
        {
            "sample_id": payload.sample_id,
            "session_id": payload.session_id,
            "sanitized_text": payload.sanitized_text,
            "metadata": payload.metadata,
            "policy_summary": payload.policy_summary,
            "public_context": payload.public_context,
        }
    )
    schema_path = Path(__file__).resolve().parent.parent / "skills" / "privacy_expense_cloud_reasoner" / "schemas" / "he_call_plan.schema.json"
    assert validate_against_schema(plan, schema_path)["valid"] is True

