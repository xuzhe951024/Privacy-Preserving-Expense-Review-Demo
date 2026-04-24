from __future__ import annotations

from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_replacement_correctness_report_matches_vault(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(
        sample_client_dinner,
        detection["resolved_entities"],
        vault,
        artifact_dir=tmp_path / "artifacts",
    )
    assert payload.replacement_report["token_vault_count_match"] is True
    assert payload.replacement_report["total_detected_sensitive_entities"] == len(payload.metadata)
    assert all(token.startswith(tuple(label + "_" for label in {meta["entity_type"] for meta in payload.metadata.values()})) for token in payload.metadata)

