from __future__ import annotations

import json
from pathlib import Path

from src.models import ExpenseSample, SanitizedPayload
from src.report_writer import sha256_file, write_json, write_markdown


def export_cloud_bundle(
    sanitized_payload: SanitizedPayload,
    sample: ExpenseSample,
    bundle_dir: str | Path = "cloud_session_bundle",
    artifact_dir: str | Path = "demo_artifacts/04_reasoner",
) -> dict[str, object]:
    bundle_root = Path(bundle_dir)
    bundle_root.mkdir(parents=True, exist_ok=True)
    artifact_root = Path(artifact_dir)
    sanitized_request = {
        "sample_id": sanitized_payload.sample_id,
        "session_id": sanitized_payload.session_id,
        "sanitized_text": sanitized_payload.sanitized_text,
        "public_context": sanitized_payload.public_context,
    }
    metadata_path = write_json(bundle_root / "placeholder_metadata.json", sanitized_payload.metadata)
    request_path = write_json(bundle_root / "sanitized_request.json", sanitized_request)
    policy_path = write_json(bundle_root / "policy_public_summary.json", sanitized_payload.policy_summary)
    write_markdown(
        bundle_root / "README.md",
        "\n".join(
            [
                "# Cloud Session Bundle",
                "",
                "This directory is safe to share with an isolated cloud-side reasoning session.",
                "",
                "- It contains sanitized text, placeholder metadata, and public policy summaries.",
                "- It does not contain raw expense text, vault contents, or local keys.",
            ]
        ),
    )
    manifest = []
    for path in sorted(bundle_root.glob("*")):
        if path.is_file():
            manifest.append({"path": path.name, "sha256": sha256_file(path)})
    write_json(artifact_root / "cloud_session_bundle_manifest.json", manifest)

    raw_values = [entity.text for entity in sample.entities]
    leakage_hits = []
    for path in bundle_root.glob("*"):
        if not path.is_file():
            continue
        blob = path.read_text(encoding="utf-8")
        for value in raw_values:
            if value in blob:
                leakage_hits.append({"file": path.name, "value": value})
    report = {
        "bundle_path": str(bundle_root),
        "contains_raw_text": False,
        "contains_vault_sqlite": (bundle_root / ".local" / "vault.sqlite").exists(),
        "contains_vault_key": (bundle_root / ".secrets" / "vault.key").exists(),
        "raw_value_hits": leakage_hits,
        "passed": len(leakage_hits) == 0,
    }
    write_json(artifact_root / "cloud_session_no_raw_access_report.json", report)
    return {
        "manifest": manifest,
        "report": report,
        "sanitized_request": sanitized_request,
        "metadata": sanitized_payload.metadata,
    }

