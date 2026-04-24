from __future__ import annotations

from pathlib import Path

import src.real_cloud_session as real_cloud_session
from src.cloud_reasoner_client import run_cloud_skill_mock


def test_real_cloud_session_outputs_stay_in_isolated_paths(sample_client_dinner, monkeypatch, tmp_path):
    paths = real_cloud_session.RealCloudSessionPaths(
        root_dir=str(tmp_path / "real_cloud_session"),
        artifact_root=str(tmp_path / "demo_artifacts" / "10_real_cloud_session"),
        result_store_dir=str(tmp_path / ".local" / "he_results_real"),
        vault_key_path=str(tmp_path / ".secrets" / "real_cloud_session" / "vault.key"),
        vault_db_path=str(tmp_path / ".local" / "real_cloud_session" / "vault.sqlite"),
        he_key_path=str(tmp_path / ".secrets" / "real_cloud_session" / "paillier_demo_key.json"),
    )

    monkeypatch.setattr(real_cloud_session, "ensure_samples", lambda: [sample_client_dinner])
    monkeypatch.setattr(
        real_cloud_session,
        "detect_sample",
        lambda sample, threshold=0.3, device="auto": {
            "rule_entities": sample.entities,
            "gliner_entities": [],
            "resolved_entities": sample.entities,
            "gliner_status": {"status": "test"},
        },
    )

    prepared = real_cloud_session.prepare_real_cloud_session(sample_id=sample_client_dinner.sample_id, paths=paths)

    assert prepared["paths"].bundle_dir.exists()
    assert prepared["paths"].handoff_dir.exists()
    assert prepared["paths"].vault_key.exists()
    assert prepared["paths"].vault_db.exists()
    assert (prepared["paths"].handoff_dir / "OPEN_IN_SECOND_SESSION.md").exists()
    assert not (tmp_path / "cloud_session_bundle").exists()
    assert not (tmp_path / "cloud_session_handoff").exists()
    assert not (tmp_path / "demo_artifacts" / "04_reasoner").exists()
    assert not (tmp_path / ".secrets" / "vault.key").exists()
    assert not (tmp_path / ".local" / "vault.sqlite").exists()

    skill_artifact_dir = tmp_path / "skill_tmp"
    skill_result = run_cloud_skill_mock(
        bundle_dir=prepared["paths"].bundle_dir,
        artifact_dir=skill_artifact_dir,
        schema_root=Path(__file__).resolve().parent.parent / "skills" / "privacy_expense_cloud_reasoner" / "schemas",
    )
    prepared["paths"].returned_plan_path.parent.mkdir(parents=True, exist_ok=True)
    prepared["paths"].returned_plan_path.write_text(
        Path(skill_artifact_dir / "he_call_plan.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    imported = real_cloud_session.import_real_cloud_plan(paths=paths)
    reassembled = real_cloud_session.run_real_cloud_reassembly(sample_id=sample_client_dinner.sample_id, paths=paths)

    assert skill_result["he_plan_validation"]["valid"] is True
    assert imported["schema_validation"]["valid"] is True
    assert imported["authorization_report"]["authorized"] is True
    assert imported["no_raw_report"]["passed"] is True
    assert reassembled["reassembly"]["final_decision_correctness"]["passed"] is True
    assert Path(reassembled["he_results"]["store_path"]).exists()
    assert (prepared["paths"].reasoner_dir / "cloud_skill_output.json").exists()
    assert (prepared["paths"].reassembly_dir / "final_user_visible_results.md").exists()
    assert (prepared["paths"].security_dir / "audit_events_real.jsonl").exists()
    assert not (tmp_path / ".local" / "he_results").exists()
