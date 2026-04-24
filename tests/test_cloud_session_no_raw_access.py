from __future__ import annotations

from src.cloud_bundle_exporter import export_cloud_bundle
from src.demo_workflow import detect_sample
from src.sanitizer import sanitize_sample
from src.vault import Vault


def test_cloud_bundle_has_no_raw_access(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    exported = export_cloud_bundle(
        payload,
        sample_client_dinner,
        bundle_dir=tmp_path / "bundle",
        artifact_dir=tmp_path / "reasoner",
    )
    assert exported["report"]["passed"] is True

