from __future__ import annotations

import json

from src.cloud_reasoner_mock import build_cloud_skill_response
from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_cloud_skill_never_requests_decrypt(sample_client_dinner, tmp_path):
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
    blob = json.dumps(plan).lower()
    for term in ["decrypt", "reveal", "lookup_vault", "print_raw"]:
        assert term not in blob

