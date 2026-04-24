#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def plan_digest(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run public-key Paillier HE evaluation over a sanitized expense bundle.")
    parser.add_argument("--bundle", default="cloud_session_bundle")
    parser.add_argument("--plan", default="session_output/he_call_plan.json")
    parser.add_argument("--output", default="session_output/cloud_skill_output.json")
    args = parser.parse_args()

    bundle_root = Path(args.bundle)
    plan = load_json(args.plan)
    public_key = load_json(bundle_root / "he_public_key.json")
    ciphertexts = load_json(bundle_root / "he_ciphertexts.json")["ciphertexts"]
    policy_operands = load_json(bundle_root / "he_policy_operands.json")["policy_operands"]
    n = int(public_key["n"])
    n_square = n * n
    encrypted_values = {token: int(payload["ciphertext"]) for token, payload in ciphertexts.items()}
    encrypted_results = {}
    he_results = []
    cents_counter = 0
    days_counter = 0

    def add(left: int, right: int) -> int:
        return (left * right) % n_square

    def negate(ciphertext: int) -> int:
        return pow(ciphertext, -1, n_square)

    for operation in plan.get("requested_he_ops", []):
        op_name = operation["op"]
        if op_name == "fhe_sum_amounts":
            handles = operation.get("ciphertext_handles", [])
            if not handles:
                raise SystemExit("fhe_sum_amounts requires ciphertext_handles")
            result_ciphertext = encrypted_values[handles[0]]
            for handle in handles[1:]:
                result_ciphertext = add(result_ciphertext, encrypted_values[handle])
            result_handle = operation.get("result_handle") or f"AMOUNT_SUM_{len(encrypted_results) + 1}"
            encrypted_results[result_handle] = result_ciphertext
            he_results.append({
                "op_id": operation["op_id"],
                "op": op_name,
                "result_handle": result_handle,
                "result_type": "encrypted_cents",
                "ciphertext": str(result_ciphertext),
            })
            continue

        input_handle = operation.get("ciphertext_handle")
        if input_handle in encrypted_results:
            input_ciphertext = encrypted_results[input_handle]
        elif input_handle in encrypted_values:
            input_ciphertext = encrypted_values[input_handle]
        else:
            raise SystemExit(f"Unknown ciphertext handle: {input_handle}")

        if op_name == "fhe_subtract_policy_cap":
            policy_key = operation["right_policy_key"]
            cents_counter += 1
            result_handle = operation.get("result_handle") or f"HE_CENTS_{cents_counter}"
            policy_ciphertext = int(policy_operands[policy_key]["ciphertext_negative_value"])
            result_ciphertext = add(input_ciphertext, policy_ciphertext)
            encrypted_results[result_handle] = result_ciphertext
            he_results.append({
                "op_id": operation["op_id"],
                "op": op_name,
                "result_handle": result_handle,
                "result_type": "encrypted_cents",
                "ciphertext": str(result_ciphertext),
            })
        elif op_name == "fhe_compare_date_window":
            days_counter += 1
            result_handle = operation.get("result_handle") or f"HE_DAYS_{days_counter}"
            operand = int(policy_operands["submission_window_days"]["ciphertext_reference_minus_window"])
            result_ciphertext = add(operand, negate(input_ciphertext))
            encrypted_results[result_handle] = result_ciphertext
            he_results.append({
                "op_id": operation["op_id"],
                "op": op_name,
                "result_handle": result_handle,
                "result_type": "encrypted_days_delta",
                "ciphertext": str(result_ciphertext),
            })
        else:
            raise SystemExit(f"Unsupported Paillier HE op: {op_name}")

    enriched = dict(plan)
    enriched["he_execution_required"] = "paillier_public_evaluator"
    enriched["he_evaluation"] = {
        "scheme": "paillier",
        "operation_mode": "public_key_homomorphic_evaluation",
        "plan_sha256": plan_digest(plan),
        "he_results": he_results,
    }
    write_json(args.output, enriched)
    print(f"Wrote Paillier HE evaluation with {len(he_results)} encrypted result(s) to {args.output}.")


if __name__ == "__main__":
    main()
