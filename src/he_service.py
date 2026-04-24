from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from src.paillier_he import PaillierPublicKey, load_or_create_private_key, load_private_key
from src.policy import get_policy_value
from src.report_writer import write_json
from src.vault import Vault


DEFAULT_HE_KEY_PATH = ".secrets/paillier_demo_key.json"
DEFAULT_REFERENCE_DATE = date(2026, 4, 30)


def _amount_to_cents(normalized_value: str | None, raw_value: str) -> int:
    if normalized_value:
        return int(round(float(normalized_value) * 100))
    return int(round(float(raw_value.replace("$", "").replace(",", "")) * 100))


def _date_to_epoch_days(normalized_value: str | None, raw_value: str) -> int:
    value = normalized_value or raw_value
    if isinstance(value, str) and value.count("-") == 2:
        return (date.fromisoformat(value) - date(1970, 1, 1)).days
    return int(value)


def _secret_to_plain_integer(secret: dict[str, Any]) -> tuple[int, str]:
    if secret["entity_type"] == "AMOUNT":
        return _amount_to_cents(secret.get("normalized_value"), secret["raw_value"]), "encrypted_cents"
    if secret["entity_type"] == "DATE":
        return _date_to_epoch_days(secret.get("normalized_value"), secret["raw_value"]), "encrypted_epoch_days"
    raise ValueError(f"Unsupported HE entity type: {secret['entity_type']}")


def _digest_plan(plan: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode("utf-8")).hexdigest()


def build_he_bundle_artifacts(
    session_id: str,
    metadata: dict[str, dict[str, Any]],
    vault: Vault,
    bundle_dir: str | Path,
    artifact_dir: str | Path,
    key_path: str | Path = DEFAULT_HE_KEY_PATH,
    key_bits: int = 1024,
    reference_date: date = DEFAULT_REFERENCE_DATE,
) -> dict[str, Any]:
    bundle_root = Path(bundle_dir)
    private_key = load_or_create_private_key(key_path, bits=key_bits)
    public_key = private_key.public_key
    ciphertexts: dict[str, dict[str, Any]] = {}

    for token, token_metadata in metadata.items():
        if token_metadata.get("entity_type") not in {"AMOUNT", "DATE"}:
            continue
        secret = vault.get_secret(session_id, token)
        plain_value, result_type = _secret_to_plain_integer(secret)
        ciphertexts[token] = {
            "token": token,
            "entity_type": secret["entity_type"],
            "ciphertext": str(public_key.encrypt(plain_value)),
            "result_type": result_type,
            "encoding": "signed_integer_mod_n",
        }

    policy_operands: dict[str, dict[str, Any]] = {}
    for policy_key in [
        "meal_cap_usd",
        "hotel_cap_usd",
        "airfare_cap_usd",
        "taxi_cap_usd",
        "software_subscription_cap_usd",
    ]:
        value = get_policy_value(policy_key)
        if value is None:
            continue
        policy_operands[policy_key] = {
            "policy_key": policy_key,
            "ciphertext_negative_value": str(public_key.encrypt(-int(value))),
            "result_type": "encrypted_cents",
            "encoding": "signed_integer_mod_n",
        }

    reference_epoch_days = (reference_date - date(1970, 1, 1)).days
    submission_window = get_policy_value("submission_window_days") or 0
    policy_operands["submission_window_days"] = {
        "policy_key": "submission_window_days",
        "ciphertext_reference_minus_window": str(public_key.encrypt(reference_epoch_days - int(submission_window))),
        "result_type": "encrypted_days_delta",
        "encoding": "signed_integer_mod_n",
    }

    public_key_payload = public_key.to_dict()
    ciphertext_payload = {
        "scheme": "paillier",
        "session_id": session_id,
        "ciphertexts": ciphertexts,
    }
    policy_payload = {
        "scheme": "paillier",
        "session_id": session_id,
        "policy_operands": policy_operands,
    }
    write_json(bundle_root / "he_public_key.json", public_key_payload)
    write_json(bundle_root / "he_ciphertexts.json", ciphertext_payload)
    write_json(bundle_root / "he_policy_operands.json", policy_payload)
    report = {
        "scheme": "paillier",
        "key_bits": public_key.bits,
        "session_id": session_id,
        "encrypted_placeholder_count": len(ciphertexts),
        "encrypted_policy_operand_count": len(policy_operands),
        "private_key_path": str(key_path),
        "bundle_files": ["he_public_key.json", "he_ciphertexts.json", "he_policy_operands.json"],
        "contains_plain_sensitive_values": False,
    }
    write_json(Path(artifact_dir) / "real_he_encryption_report.json", report)
    return {
        "public_key": public_key_payload,
        "ciphertexts": ciphertext_payload,
        "policy_operands": policy_payload,
        "report": report,
    }


def _load_public_context(bundle_dir: str | Path) -> tuple[PaillierPublicKey, dict[str, Any], dict[str, Any]]:
    bundle_root = Path(bundle_dir)
    public_key = PaillierPublicKey.from_dict(json.loads((bundle_root / "he_public_key.json").read_text(encoding="utf-8")))
    ciphertexts = json.loads((bundle_root / "he_ciphertexts.json").read_text(encoding="utf-8"))["ciphertexts"]
    policy_operands = json.loads((bundle_root / "he_policy_operands.json").read_text(encoding="utf-8"))["policy_operands"]
    return public_key, ciphertexts, policy_operands


def evaluate_he_plan_public(
    plan: dict[str, Any],
    bundle_dir: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    public_key, ciphertexts, policy_operands = _load_public_context(bundle_dir)
    encrypted_values = {token: int(payload["ciphertext"]) for token, payload in ciphertexts.items()}
    encrypted_results: dict[str, int] = {}
    result_types: dict[str, str] = {}
    he_results: list[dict[str, Any]] = []
    cents_counter = 0
    days_counter = 0

    for operation in plan.get("requested_he_ops", []):
        op_name = operation["op"]
        if op_name == "fhe_sum_amounts":
            handles = operation.get("ciphertext_handles", [])
            if not handles:
                raise ValueError("fhe_sum_amounts requires ciphertext_handles.")
            total_ciphertext = encrypted_values[handles[0]]
            for handle in handles[1:]:
                total_ciphertext = public_key.add(total_ciphertext, encrypted_values[handle])
            result_handle = operation.get("result_handle") or f"AMOUNT_SUM_{len(encrypted_results) + 1}"
            encrypted_results[result_handle] = total_ciphertext
            result_types[result_handle] = "encrypted_cents"
            he_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": op_name,
                    "result_handle": result_handle,
                    "result_type": "encrypted_cents",
                    "ciphertext": str(total_ciphertext),
                }
            )
            continue

        input_handle = operation.get("ciphertext_handle")
        if input_handle in encrypted_results:
            input_ciphertext = encrypted_results[input_handle]
        elif input_handle in encrypted_values:
            input_ciphertext = encrypted_values[input_handle]
        else:
            raise ValueError(f"Unknown ciphertext handle: {input_handle}")

        if op_name == "fhe_subtract_policy_cap":
            policy_key = operation["right_policy_key"]
            if policy_key not in policy_operands:
                raise ValueError(f"Missing HE policy operand: {policy_key}")
            cents_counter += 1
            result_handle = operation.get("result_handle") or f"HE_CENTS_{cents_counter}"
            policy_ciphertext = int(policy_operands[policy_key]["ciphertext_negative_value"])
            result_ciphertext = public_key.add(input_ciphertext, policy_ciphertext)
            encrypted_results[result_handle] = result_ciphertext
            result_types[result_handle] = "encrypted_cents"
            he_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": op_name,
                    "result_handle": result_handle,
                    "result_type": "encrypted_cents",
                    "ciphertext": str(result_ciphertext),
                }
            )
        elif op_name == "fhe_compare_date_window":
            days_counter += 1
            result_handle = operation.get("result_handle") or f"HE_DAYS_{days_counter}"
            operand = int(policy_operands["submission_window_days"]["ciphertext_reference_minus_window"])
            negative_date_ciphertext = public_key.negate(input_ciphertext)
            result_ciphertext = public_key.add(operand, negative_date_ciphertext)
            encrypted_results[result_handle] = result_ciphertext
            result_types[result_handle] = "encrypted_days_delta"
            he_results.append(
                {
                    "op_id": operation["op_id"],
                    "op": op_name,
                    "result_handle": result_handle,
                    "result_type": "encrypted_days_delta",
                    "ciphertext": str(result_ciphertext),
                }
            )
        else:
            raise ValueError(f"Unsupported real HE op for Paillier evaluator: {op_name}")

    evaluation = {
        "scheme": "paillier",
        "operation_mode": "public_key_homomorphic_evaluation",
        "plan_sha256": _digest_plan(plan),
        "he_results": he_results,
    }
    if output_path is not None:
        write_json(output_path, evaluation)
    return evaluation


def decrypt_he_results(
    he_evaluation: dict[str, Any],
    session_id: str,
    key_path: str | Path,
    result_store_dir: str | Path,
) -> dict[str, Any]:
    private_key = load_private_key(key_path)
    private_values: dict[str, dict[str, Any]] = {}
    for result in he_evaluation.get("he_results", []):
        value = private_key.decrypt(int(result["ciphertext"]))
        private_values[result["result_handle"]] = {
            "type": result["result_type"],
            "value": value,
            "scheme": "paillier",
        }
    result_store_root = Path(result_store_dir)
    result_store_root.mkdir(parents=True, exist_ok=True)
    store_path = result_store_root / f"{session_id}.json"
    store_path.write_text(json.dumps(private_values, indent=2) + "\n", encoding="utf-8")
    return {"private_values": private_values, "store_path": str(store_path)}


def extract_plan_and_evaluation(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if "he_plan" in payload:
        return payload["he_plan"], payload.get("he_evaluation")
    plan = dict(payload)
    he_evaluation = plan.pop("he_evaluation", None)
    plan.pop("he_execution_required", None)
    return plan, he_evaluation


def attach_evaluation_to_plan(plan: dict[str, Any], he_evaluation: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(plan)
    enriched["he_evaluation"] = he_evaluation
    enriched["he_execution_required"] = "paillier_public_evaluator"
    return enriched


def execute_he_plan(
    plan: dict[str, Any],
    session_id: str,
    vault: Vault | None = None,
    artifact_dir: str | Path = "demo_artifacts/05_reassembly",
    result_store_dir: str | Path = ".local/he_results",
    bundle_dir: str | Path = "cloud_session_bundle",
    key_path: str | Path = DEFAULT_HE_KEY_PATH,
    submission_reference_epoch_days: int | None = None,
) -> dict[str, Any]:
    del vault, submission_reference_epoch_days
    he_evaluation = plan.get("he_evaluation")
    if he_evaluation is None:
        he_evaluation = evaluate_he_plan_public(plan, bundle_dir=bundle_dir)
    decryption = decrypt_he_results(
        he_evaluation,
        session_id=session_id,
        key_path=key_path,
        result_store_dir=result_store_dir,
    )
    he_results = {"he_results": he_evaluation["he_results"], "scheme": "paillier"}
    write_json(Path(artifact_dir) / "he_ops_results_encrypted_handles.json", he_results)
    write_json(
        Path(artifact_dir) / "real_he_execution_report.json",
        {
            "scheme": "paillier",
            "operation_mode": he_evaluation["operation_mode"],
            "result_count": len(he_evaluation["he_results"]),
            "store_path": decryption["store_path"],
            "used_real_homomorphic_evaluation": True,
        },
    )
    return {**he_results, **decryption}


def load_private_he_results(session_id: str, result_store_dir: str | Path = ".local/he_results") -> dict[str, Any]:
    store_path = Path(result_store_dir) / f"{session_id}.json"
    return json.loads(store_path.read_text(encoding="utf-8"))
