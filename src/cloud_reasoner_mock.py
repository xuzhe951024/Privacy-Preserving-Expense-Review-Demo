from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.policy import ALLOWED_HE_OPS
from src.report_writer import write_json

BANNED_REASONER_TERMS = {"decrypt", "reveal", "lookup_vault", "print_raw"}


def _amount_handles(metadata: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(token for token, payload in metadata.items() if payload.get("entity_type") == "AMOUNT")


def _date_handles(metadata: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(token for token, payload in metadata.items() if payload.get("entity_type") == "DATE")


def build_local_reasoner_response(sanitized_request: dict[str, Any]) -> dict[str, Any]:
    metadata = sanitized_request["metadata"]
    context = sanitized_request.get("public_context", {})
    amount_handles = _amount_handles(metadata)
    requested_local_ops: list[dict[str, Any]] = []
    if context.get("requires_sum") and len(amount_handles) > 1:
        requested_local_ops.append({"op": "sum", "left": amount_handles, "return_as": "AMOUNT_SUM_1"})
        amount_target = "AMOUNT_SUM_1"
    elif amount_handles:
        amount_target = amount_handles[0]
    else:
        amount_target = None

    policy_key = context.get("policy_key")
    policy_missing = policy_key == "unknown_policy_key"

    if amount_target and policy_key and not policy_missing:
        requested_local_ops.append(
            {
                "op": "compare_policy_cap",
                "left": amount_target,
                "right_policy_key": policy_key,
            }
        )
    if amount_target and policy_key and not policy_missing:
        requested_local_ops.append(
            {
                "op": "subtract",
                "left": amount_target,
                "right_policy_key": policy_key,
            }
        )
    if _date_handles(metadata):
        requested_local_ops.append({"op": "compare_submission_window", "left": _date_handles(metadata)[0]})

    missing_items = list(sanitized_request.get("public_context", {}).get("missing_items", []))
    if not sanitized_request.get("public_context", {}).get("receipt_attached", True):
        missing_items.append("receipt")

    decision = "needs_local_policy_ops" if requested_local_ops else "needs_human_review"
    if context.get("duplicate_invoice") or policy_missing or context.get("malformed_amount"):
        decision = "needs_human_review"
    return {
        "workflow_type": "expense_review",
        "decision": decision,
        "requested_local_ops": requested_local_ops,
        "missing_items": sorted(set(missing_items)),
        "rationale": [
            "The cloud reasoner only saw sanitized placeholders.",
            "Sensitive fields require local policy operations before final routing.",
        ],
    }


def build_cloud_skill_response(sanitized_request: dict[str, Any]) -> dict[str, Any]:
    metadata = sanitized_request["metadata"]
    context = sanitized_request.get("public_context", {})
    amount_handles = _amount_handles(metadata)
    requested_he_ops: list[dict[str, Any]] = []
    next_id = 1
    comparison_handle = None

    if context.get("requires_sum") and len(amount_handles) > 1:
        comparison_handle = "AMOUNT_SUM_1"
        requested_he_ops.append(
            {
                "op_id": f"op_{next_id:03d}",
                "op": "fhe_sum_amounts",
                "ciphertext_handles": amount_handles,
                "result_handle": comparison_handle,
                "return_as": "encrypted_cents",
            }
        )
        next_id += 1
    elif amount_handles:
        comparison_handle = amount_handles[0]

    if comparison_handle and context.get("policy_key"):
        requested_he_ops.append(
            {
                "op_id": f"op_{next_id:03d}",
                "op": "fhe_subtract_policy_cap",
                "ciphertext_handle": comparison_handle,
                "right_policy_key": context["policy_key"],
                "return_as": "encrypted_cents",
            }
        )
        next_id += 1
    if _date_handles(metadata):
        requested_he_ops.append(
            {
                "op_id": f"op_{next_id:03d}",
                "op": "fhe_compare_date_window",
                "ciphertext_handle": _date_handles(metadata)[0],
                "right_policy_key": "submission_window_days",
                "return_as": "encrypted_days_delta",
            }
        )

    decision = "needs_he_ops" if requested_he_ops else "needs_human_review"
    if context.get("duplicate_invoice") or context.get("policy_key") == "unknown_policy_key" or context.get("malformed_amount"):
        decision = "needs_human_review"
        requested_he_ops = []

    return {
        "workflow_type": "expense_review",
        "decision": decision,
        "non_sensitive_reasoning": [
            f"The sanitized expense appears to be a {context.get('expense_type', 'review request')}.",
            "Sensitive numeric placeholders require Paillier encrypted policy validation.",
        ],
        "requested_he_ops": requested_he_ops,
        "missing_items": ["receipt"] if not context.get("receipt_attached", True) else [],
    }


def validate_authorized_he_ops(plan: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    unauthorized_ops = []
    unknown_handles = []
    banned_requests = []
    derived_handles: dict[str, set[str]] = {}
    blob = json.dumps(plan).lower()
    for term in BANNED_REASONER_TERMS:
        if term in blob:
            banned_requests.append(term)

    for operation in plan.get("requested_he_ops", []):
        op_name = operation.get("op")
        if op_name not in ALLOWED_HE_OPS:
            unauthorized_ops.append({"op_id": operation.get("op_id"), "reason": "op_not_allowlisted", "op": op_name})
            continue
        handles = operation.get("ciphertext_handles") or [operation.get("ciphertext_handle")]
        allowed = True
        inherited_permissions: set[str] = set()
        for handle in handles:
            if handle in metadata:
                token_allowed = set(metadata[handle].get("allowed_he_ops", []))
                inherited_permissions.update(token_allowed)
                if op_name not in token_allowed:
                    allowed = False
                    unauthorized_ops.append(
                        {"op_id": operation.get("op_id"), "reason": "handle_op_not_allowed", "handle": handle, "op": op_name}
                    )
            elif handle in derived_handles:
                token_allowed = derived_handles[handle]
                inherited_permissions.update(token_allowed)
                if op_name not in token_allowed:
                    allowed = False
                    unauthorized_ops.append(
                        {"op_id": operation.get("op_id"), "reason": "derived_handle_op_not_allowed", "handle": handle, "op": op_name}
                    )
            else:
                allowed = False
                unknown_handles.append({"op_id": operation.get("op_id"), "handle": handle})
        if allowed and operation.get("result_handle"):
            result_handle = operation["result_handle"]
            if op_name == "fhe_sum_amounts":
                derived_handles[result_handle] = {"fhe_subtract_policy_cap"}
            else:
                derived_handles[result_handle] = inherited_permissions or {op_name}

    return {
        "authorized": not unauthorized_ops and not unknown_handles and not banned_requests,
        "unauthorized_ops": unauthorized_ops,
        "unknown_handles": unknown_handles,
        "banned_requests": banned_requests,
    }


def write_reasoner_artifacts(
    sanitized_request: dict[str, Any],
    local_response: dict[str, Any],
    cloud_response: dict[str, Any],
    artifact_dir: str | Path = "demo_artifacts/04_reasoner",
) -> dict[str, Any]:
    artifact_root = Path(artifact_dir)
    authorization_report = validate_authorized_he_ops(cloud_response, sanitized_request["metadata"])
    provenance = {
        "session_label": "mock_cloud_session",
        "execution_mode": "repository_internal_mock",
        "producer": "src.cloud_reasoner_mock.build_cloud_skill_response",
        "separate_codex_session": False,
        "interpretation_note": (
            "This artifact was produced by the repository-internal mock reasoner. "
            "Use it as a baseline or control path, not as output from a separately executed Codex session."
        ),
    }
    write_json(artifact_root / "cloud_request_mock.json", sanitized_request)
    write_json(artifact_root / "reasoner_response_mock.json", local_response)
    write_json(artifact_root / "requested_local_ops.json", local_response.get("requested_local_ops", []))
    write_json(artifact_root / "cloud_skill_input.json", sanitized_request)
    write_json(artifact_root / "cloud_skill_output.json", cloud_response)
    write_json(artifact_root / "he_call_plan.json", cloud_response)
    write_json(artifact_root / "mock_session_provenance.json", provenance)
    write_json(artifact_root / "unauthorized_ops_report.json", authorization_report)
    write_json(artifact_root / "he_call_authorization_report.json", authorization_report)
    return authorization_report
