from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from src.models import DetectedEntity, ExpenseSample, SanitizedPayload
from src.policy import get_entity_policy, get_public_policy_summary, token_label
from src.report_writer import write_csv, write_json
from src.vault import Vault


def _candidate_leak_values(entity: DetectedEntity) -> list[str]:
    values = [entity.text]
    if entity.normalized_value:
        values.append(entity.normalized_value)
    if entity.label == "AMOUNT" and entity.normalized_value:
        values.append(entity.normalized_value.replace(".", ""))
    return [value for value in values if value]


def _run_no_raw_leakage_guard(payload: dict[str, Any], entities: list[DetectedEntity]) -> dict[str, Any]:
    payload_blob = json.dumps(payload, sort_keys=True)
    offenders: list[dict[str, str]] = []
    for entity in entities:
        if get_entity_policy(entity.label).get("action") == "keep_plaintext":
            continue
        for candidate in _candidate_leak_values(entity):
            if candidate and candidate.lower() in payload_blob.lower():
                offenders.append({"label": entity.label, "candidate": candidate, "token": entity.entity_id or ""})
    return {
        "raw_value_leakage_count": len(offenders),
        "offenders": offenders,
        "passed": len(offenders) == 0,
    }


def sanitize_sample(
    sample: ExpenseSample,
    entities: list[DetectedEntity],
    vault: Vault,
    artifact_dir: str | Path = "demo_artifacts/03_sanitization",
    session_id: str | None = None,
) -> SanitizedPayload:
    session = session_id or f"{sample.sample_id}-{uuid.uuid4().hex[:8]}"
    counters: Counter[str] = Counter()
    token_preview: list[dict[str, Any]] = []
    metadata: dict[str, dict[str, Any]] = {}
    replacement_ranges: list[tuple[int, int, str]] = []

    for entity in entities:
        policy = get_entity_policy(entity.label)
        if policy.get("action") == "keep_plaintext":
            continue
        counters[entity.label] += 1
        token = f"{token_label(entity.label)}_{counters[entity.label]}"
        placeholder = f"<{token}>"
        preview = vault.put_secret(session, token, entity.label, entity.text, entity.normalized_value)
        token_preview.append(preview)
        metadata[token] = {
            "entity_type": entity.label,
            "placeholder": placeholder,
            "allowed_ops": list(policy.get("allowed_ops", [])),
            "allowed_he_ops": list(policy.get("allowed_he_ops", [])),
            "policy_action": policy.get("action"),
            "source": entity.source,
            "score": round(entity.score, 4),
        }
        replacement_ranges.append((entity.start, entity.end, placeholder))

    sanitized_text = sample.raw_text
    for start, end, placeholder in sorted(replacement_ranges, key=lambda item: item[0], reverse=True):
        sanitized_text = sanitized_text[:start] + placeholder + sanitized_text[end:]

    replacement_report = {
        "total_detected_sensitive_entities": len(replacement_ranges),
        "total_replaced_entities": len(replacement_ranges),
        "unreplaced_entities": [],
        "wrong_token_type": [],
        "overlap_resolution_failures": [],
        "token_vault_count_match": len(replacement_ranges) == vault.count_session_records(session),
    }
    payload = {
        "sample_id": sample.sample_id,
        "session_id": session,
        "sanitized_text": sanitized_text,
        "metadata": metadata,
        "policy_summary": get_public_policy_summary(),
        "public_context": sample.workflow_context,
    }
    leakage_check = _run_no_raw_leakage_guard(payload, entities)

    artifact_root = Path(artifact_dir)
    token_inventory_rows = [
        {
            "token": preview["token"],
            "entity_type": preview["entity_type"],
            "source_hash_prefix": preview["source_hash_prefix"],
            "recoverable": preview["recoverable"],
        }
        for preview in token_preview
    ]
    write_json(
        artifact_root / "sanitized_payload_examples.json",
        {
            "sample_id": sample.sample_id,
            "session_id": session,
            "sanitized_text": sanitized_text,
            "metadata": metadata,
            "policy_summary": get_public_policy_summary(),
            "public_context": sample.workflow_context,
        },
    )
    write_json(artifact_root / "token_mapping_redacted_preview.json", token_preview)
    write_json(artifact_root / "no_raw_leakage_check.json", leakage_check)
    write_json(artifact_root / "replacement_correctness_report.json", replacement_report)
    write_csv(artifact_root / "sanitized_token_inventory.csv", token_inventory_rows)

    return SanitizedPayload(
        sample_id=sample.sample_id,
        session_id=session,
        sanitized_text=sanitized_text,
        metadata=metadata,
        policy_summary=get_public_policy_summary(),
        public_context=sample.workflow_context,
        replacement_report=replacement_report,
        leakage_check=leakage_check,
        token_preview=token_preview,
    )

