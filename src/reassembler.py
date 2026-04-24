from __future__ import annotations

from pathlib import Path
from typing import Any

from src.audit import AuditLogger
from src.he_service import load_private_he_results
from src.models import ExpenseSample, SanitizedPayload
from src.policy import get_policy_value
from src.report_writer import write_json, write_markdown


def _cents_to_usd(value: int) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    return f"{sign}${absolute / 100:.2f}"


def reassemble_results(
    sample: ExpenseSample,
    sanitized_payload: SanitizedPayload,
    he_plan: dict[str, Any],
    he_results: dict[str, Any],
    audit_logger: AuditLogger,
    artifact_dir: str | Path = "demo_artifacts/05_reassembly",
    result_store_dir: str | Path = ".local/he_results",
) -> dict[str, Any]:
    artifact_root = Path(artifact_dir)
    private_results = load_private_he_results(sanitized_payload.session_id, result_store_dir=result_store_dir)
    write_json(artifact_root / "he_ops_local_decryption_report.json", {"local_decryption_results": private_results})

    local_ops_results = []
    compare_exceeds = False
    delta_cents = 0
    for operation, encrypted_result in zip(he_plan.get("requested_he_ops", []), he_results.get("he_results", [])):
        result_handle = encrypted_result["result_handle"]
        decrypted = private_results[result_handle]
        if operation["op"] == "fhe_subtract_policy_cap":
            delta_cents = int(decrypted["value"])
            compare_exceeds = delta_cents > 0
            local_ops_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": "decrypt_policy_delta_and_compare_locally",
                    "ciphertext_handle": operation["ciphertext_handle"],
                    "right_policy_key": operation["right_policy_key"],
                    "interpreted_result": {
                        "delta_cents": delta_cents,
                        "comparison": "exceeds" if compare_exceeds else "within_cap",
                    },
                }
            )
        elif operation["op"] == "fhe_compare_date_window":
            date_delta = int(decrypted["value"])
            local_ops_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": "decrypt_submission_window_delta_locally",
                    "ciphertext_handle": operation["ciphertext_handle"],
                    "right_policy_key": operation["right_policy_key"],
                    "interpreted_result": {
                        "delta_days": date_delta,
                        "within_window": date_delta <= 0,
                    },
                }
            )
        elif operation["op"] == "fhe_sum_amounts":
            local_ops_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": "sum",
                    "ciphertext_handles": operation["ciphertext_handles"],
                    "interpreted_result": int(decrypted["value"]),
                }
            )

    missing_items = list(sample.expected_missing_items)
    if not sanitized_payload.public_context.get("receipt_attached", True) and "receipt" not in missing_items:
        missing_items.append("receipt")

    if sanitized_payload.public_context.get("duplicate_invoice"):
        actual_decision = "needs_human_review"
    elif sanitized_payload.public_context.get("malformed_amount"):
        actual_decision = "needs_human_review"
    elif sanitized_payload.public_context.get("policy_key") == "unknown_policy_key":
        actual_decision = "needs_human_review"
    elif sanitized_payload.public_context.get("expense_type") in {"review_contact", "ambiguous_note"}:
        actual_decision = "needs_human_review"
    elif missing_items:
        actual_decision = "needs_employee_followup"
    elif compare_exceeds:
        actual_decision = "needs_manager_approval"
    else:
        actual_decision = "auto_approve"

    policy_key = sanitized_payload.public_context.get("policy_key")
    if policy_key == "unknown_policy_key":
        actual_compare_result = "needs_human_review"
        actual_delta_usd = None
    else:
        actual_compare_result = "exceeds" if compare_exceeds else "within_cap"
        actual_delta_usd = f"{abs(delta_cents) / 100:.2f}"

    expected_compare = next((item for item in sample.expected_policy_ops if item.get("op") == "compare_policy_cap"), None)
    policy_ops_correctness = {
        "sample_id": sample.sample_id,
        "expected_compare_result": expected_compare.get("expected_result") if expected_compare else None,
        "actual_compare_result": actual_compare_result,
        "expected_delta_usd": expected_compare.get("expected_delta_usd") if expected_compare else None,
        "actual_delta_usd": actual_delta_usd if expected_compare else None,
        "passed": (
            expected_compare is None
            or (
                actual_compare_result == expected_compare.get("expected_result")
                and actual_delta_usd == expected_compare.get("expected_delta_usd")
            )
        ),
    }
    final_decision_correctness = {
        "sample_id": sample.sample_id,
        "expected_final_decision": sample.expected_final_decision,
        "actual_final_decision": actual_decision,
        "passed": sample.expected_final_decision == actual_decision,
    }

    write_json(artifact_root / "local_ops_results.json", local_ops_results)
    write_json(artifact_root / "policy_ops_correctness_report.json", policy_ops_correctness)
    write_json(artifact_root / "final_decision_correctness_report.json", final_decision_correctness)
    write_markdown(
        artifact_root / "final_user_visible_results.md",
        "\n".join(
            [
                "# Final User Visible Result",
                "",
                f"- Sample ID: {sample.sample_id}",
                f"- Final decision: {actual_decision}",
                f"- Missing items: {', '.join(missing_items) if missing_items else 'None'}",
                f"- Policy delta: {_cents_to_usd(delta_cents)}",
                f"- Policy key: {sanitized_payload.public_context.get('policy_key', 'N/A')}",
            ]
        ),
    )
    audit_logger.record(
        "reassembly",
        "local_reassembly_complete",
        sample_id=sample.sample_id,
        final_decision=actual_decision,
        missing_items=missing_items,
        policy_key=sanitized_payload.public_context.get("policy_key"),
        policy_value=get_policy_value(sanitized_payload.public_context.get("policy_key", "")),
    )
    write_json(artifact_root / "end_to_end_trace.json", audit_logger.to_list())
    return {
        "local_ops_results": local_ops_results,
        "policy_ops_correctness": policy_ops_correctness,
        "final_decision_correctness": final_decision_correctness,
        "actual_final_decision": actual_decision,
    }
