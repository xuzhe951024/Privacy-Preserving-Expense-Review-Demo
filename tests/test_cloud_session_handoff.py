from __future__ import annotations

from pathlib import Path

from src.cloud_bundle_exporter import export_cloud_bundle
from src.cloud_session_handoff import prepare_isolated_cloud_session_handoff
from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_isolated_cloud_session_handoff_contains_only_safe_files(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    export_cloud_bundle(
        payload,
        sample_client_dinner,
        bundle_dir=tmp_path / "bundle",
        artifact_dir=tmp_path / "reasoner",
        vault=vault,
        he_key_path=tmp_path / "paillier.key.json",
    )
    handoff = prepare_isolated_cloud_session_handoff(
        bundle_dir=tmp_path / "bundle",
        skill_dir=Path(__file__).resolve().parent.parent / "skills" / "privacy_expense_cloud_reasoner",
        handoff_dir=tmp_path / "handoff",
        artifact_dir=tmp_path / "reasoner",
    )
    assert handoff["report"]["passed"] is True
    assert (tmp_path / "handoff" / "OPEN_IN_SECOND_SESSION.md").exists()
    assert (tmp_path / "handoff" / "session_output" / "README.md").exists()
    assert (tmp_path / "handoff" / "cloud_session_bundle" / "sanitized_request.json").exists()
    assert (tmp_path / "handoff" / "cloud_session_bundle" / "he_public_key.json").exists()
    assert (tmp_path / "handoff" / "tools" / "run_real_he_eval.py").exists()
    assert (tmp_path / "handoff" / "skills" / "privacy_expense_cloud_reasoner" / "SKILL.md").exists()
