from __future__ import annotations

from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_sanitized_payload_has_no_raw_leakage(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(
        sample_client_dinner,
        detection["resolved_entities"],
        vault,
        artifact_dir=tmp_path / "artifacts",
    )
    assert payload.leakage_check["passed"] is True
    for entity in detection["resolved_entities"]:
        assert entity.text not in payload.sanitized_text

