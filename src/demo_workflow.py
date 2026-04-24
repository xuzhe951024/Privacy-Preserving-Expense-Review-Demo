from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from src.audit import AuditLogger
from src.cloud_bundle_exporter import export_cloud_bundle
from src.cloud_reasoner_client import run_cloud_skill_mock
from src.detector_gliner import detect_gliner_entities, detector_status_report
from src.detector_rules import detect_rule_entities
from src.entity_resolver import resolve_entities
from src.he_service_mock import execute_he_plan
from src.models import ExpenseSample
from src.reassembler import reassemble_results
from src.sanitizer import sanitize_sample
from src.vault import Vault


def detect_sample(sample: ExpenseSample, threshold: float = 0.3, device: str = "auto") -> dict[str, Any]:
    rule_entities = detect_rule_entities(sample.raw_text)
    gliner_run = detect_gliner_entities(sample.raw_text, threshold=threshold, device=device)
    resolved_entities = resolve_entities(rule_entities, gliner_run.entities)
    return {
        "rule_entities": rule_entities,
        "gliner_entities": gliner_run.entities,
        "resolved_entities": resolved_entities,
        "gliner_status": detector_status_report(gliner_run),
    }


def run_demo_flow(
    sample: ExpenseSample,
    threshold: float = 0.3,
    device: str = "auto",
    artifact_root: str | Path = ".",
    bundle_dir: str | Path = "cloud_session_bundle",
    vault: Vault | None = None,
) -> dict[str, Any]:
    project_root = Path(artifact_root)
    source_root = Path(__file__).resolve().parent.parent
    audit_logger = AuditLogger()
    local_vault = vault or Vault(project_root / ".secrets" / "vault.key", project_root / ".local" / "vault.sqlite")

    detection = detect_sample(sample, threshold=threshold, device=device)
    audit_logger.record(
        "detect",
        "local_detection_complete",
        sample_id=sample.sample_id,
        resolved_entity_count=len(detection["resolved_entities"]),
        gliner_status=detection["gliner_status"],
    )

    sanitized_payload = sanitize_sample(
        sample,
        detection["resolved_entities"],
        local_vault,
        artifact_dir=project_root / "demo_artifacts" / "03_sanitization",
    )
    audit_logger.record(
        "sanitize",
        "local_sanitization_complete",
        sample_id=sample.sample_id,
        session_id=sanitized_payload.session_id,
        token_count=len(sanitized_payload.metadata),
        leakage_passed=sanitized_payload.leakage_check["passed"],
    )

    bundle_export = export_cloud_bundle(
        sanitized_payload,
        sample,
        bundle_dir=project_root / bundle_dir,
        artifact_dir=project_root / "demo_artifacts" / "04_reasoner",
    )
    audit_logger.record(
        "request",
        "cloud_bundle_exported",
        sample_id=sample.sample_id,
        session_id=sanitized_payload.session_id,
        manifest_entries=len(bundle_export["manifest"]),
        no_raw_access_passed=bundle_export["report"]["passed"],
    )

    cloud_skill = run_cloud_skill_mock(
        bundle_dir=project_root / bundle_dir,
        artifact_dir=project_root / "demo_artifacts" / "04_reasoner",
        schema_root=source_root / "skills" / "privacy_expense_cloud_reasoner" / "schemas",
    )
    audit_logger.record(
        "reason",
        "cloud_skill_complete",
        sample_id=sample.sample_id,
        session_id=sanitized_payload.session_id,
        decision=cloud_skill["cloud_response"]["decision"],
        schema_valid=cloud_skill["he_plan_validation"]["valid"],
        authorization_valid=cloud_skill["authorization_report"]["authorized"],
    )

    if not cloud_skill["he_plan_validation"]["valid"] or not cloud_skill["authorization_report"]["authorized"]:
        raise RuntimeError("Unsafe or invalid HE plan detected. The demo stops instead of falling back to an unsafe path.")

    he_results = execute_he_plan(
        cloud_skill["cloud_response"],
        sanitized_payload.session_id,
        local_vault,
        artifact_dir=project_root / "demo_artifacts" / "05_reassembly",
        result_store_dir=project_root / ".local" / "he_results",
        submission_reference_epoch_days=(date(2026, 4, 30) - date(1970, 1, 1)).days,
    )
    audit_logger.record(
        "local_ops",
        "he_mock_complete",
        sample_id=sample.sample_id,
        session_id=sanitized_payload.session_id,
        he_result_count=len(he_results["he_results"]),
    )

    reassembly = reassemble_results(
        sample,
        sanitized_payload,
        cloud_skill["cloud_response"],
        he_results,
        audit_logger,
        artifact_dir=project_root / "demo_artifacts" / "05_reassembly",
        result_store_dir=project_root / ".local" / "he_results",
    )

    audit_logger.write_jsonl(project_root / "demo_artifacts" / "06_security" / "audit_events.jsonl")
    return {
        "audit_logger": audit_logger,
        "detection": detection,
        "sanitized_payload": sanitized_payload,
        "bundle_export": bundle_export,
        "cloud_skill": cloud_skill,
        "he_results": he_results,
        "reassembly": reassembly,
        "vault": local_vault,
    }
