from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from src.policy import get_policy_value
from src.report_writer import write_json
from src.vault import Vault


def _amount_to_cents(normalized_value: str | None, raw_value: str) -> int:
    if normalized_value:
        return int(round(float(normalized_value) * 100))
    return int(round(float(raw_value.replace("$", "").replace(",", "")) * 100))


def _resolve_handle_value(
    handle: str,
    session_id: str,
    vault: Vault,
    private_values: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if handle in private_values:
        return private_values[handle]
    secret = vault.get_secret(session_id, handle)
    if secret["entity_type"] == "AMOUNT":
        value = _amount_to_cents(secret.get("normalized_value"), secret["raw_value"])
        return {"type": "encrypted_cents", "value": value}
    if secret["entity_type"] == "DATE":
        normalized_value = secret.get("normalized_value") or "0"
        if isinstance(normalized_value, str) and normalized_value.count("-") == 2:
            normalized_value = str((date.fromisoformat(normalized_value) - date(1970, 1, 1)).days)
        return {"type": "encrypted_int", "value": int(normalized_value)}
    raise ValueError(f"Unsupported handle type for HE mock: {secret['entity_type']}")


def execute_he_plan(
    plan: dict[str, Any],
    session_id: str,
    vault: Vault,
    artifact_dir: str | Path = "demo_artifacts/05_reassembly",
    result_store_dir: str | Path = ".local/he_results",
    submission_reference_epoch_days: int | None = None,
) -> dict[str, Any]:
    artifact_root = Path(artifact_dir)
    result_store_root = Path(result_store_dir)
    result_store_root.mkdir(parents=True, exist_ok=True)
    private_values: dict[str, dict[str, Any]] = {}
    he_results: list[dict[str, Any]] = []
    bool_counter = 0
    cents_counter = 0

    for operation in plan.get("requested_he_ops", []):
        op_name = operation["op"]
        if op_name == "fhe_sum_amounts":
            values = [
                _resolve_handle_value(handle, session_id, vault, private_values)["value"]
                for handle in operation.get("ciphertext_handles", [])
            ]
            result_handle = operation.get("result_handle") or f"AMOUNT_SUM_{len(private_values) + 1}"
            private_values[result_handle] = {"type": "encrypted_cents", "value": sum(values)}
            he_results.append({"op_id": operation["op_id"], "result_handle": result_handle, "result_type": "encrypted_cents"})
            continue

        input_handle = operation.get("ciphertext_handle")
        resolved = _resolve_handle_value(input_handle, session_id, vault, private_values)
        policy_key = operation.get("right_policy_key")
        policy_value = get_policy_value(policy_key) if policy_key else None

        if op_name == "fhe_compare_policy_cap":
            bool_counter += 1
            result_handle = f"HE_BOOL_{bool_counter}"
            private_values[result_handle] = {"type": "encrypted_bool", "value": resolved["value"] > int(policy_value or 0)}
            he_results.append({"op_id": operation["op_id"], "result_handle": result_handle, "result_type": "encrypted_bool"})
        elif op_name == "fhe_subtract_policy_cap":
            cents_counter += 1
            result_handle = f"HE_CENTS_{cents_counter}"
            private_values[result_handle] = {"type": "encrypted_cents", "value": resolved["value"] - int(policy_value or 0)}
            he_results.append({"op_id": operation["op_id"], "result_handle": result_handle, "result_type": "encrypted_cents"})
        elif op_name == "fhe_compare_date_window":
            bool_counter += 1
            result_handle = f"HE_BOOL_{bool_counter}"
            reference = submission_reference_epoch_days or 0
            private_values[result_handle] = {
                "type": "encrypted_bool",
                "value": (reference - resolved["value"]) <= int(policy_value or 0),
            }
            he_results.append({"op_id": operation["op_id"], "result_handle": result_handle, "result_type": "encrypted_bool"})
        elif op_name == "fhe_min_policy_cap":
            cents_counter += 1
            result_handle = f"HE_CENTS_{cents_counter}"
            private_values[result_handle] = {"type": "encrypted_cents", "value": min(resolved["value"], int(policy_value or 0))}
            he_results.append({"op_id": operation["op_id"], "result_handle": result_handle, "result_type": "encrypted_cents"})
        else:
            raise ValueError(f"Unsupported HE mock op: {op_name}")

    store_path = result_store_root / f"{session_id}.json"
    store_path.write_text(json.dumps(private_values, indent=2) + "\n", encoding="utf-8")
    write_json(artifact_root / "he_ops_results_encrypted_handles.json", {"he_results": he_results})
    return {"he_results": he_results, "private_values": private_values, "store_path": str(store_path)}


def load_private_he_results(session_id: str, result_store_dir: str | Path = ".local/he_results") -> dict[str, Any]:
    store_path = Path(result_store_dir) / f"{session_id}.json"
    return json.loads(store_path.read_text(encoding="utf-8"))
