from __future__ import annotations

import shutil
from pathlib import Path

from src.report_writer import sha256_file, write_json, write_markdown


ALLOWED_TOP_LEVEL_PATHS = {
    "README.md",
    "OPEN_IN_SECOND_SESSION.md",
    "handoff_manifest.json",
    "cloud_session_bundle",
    "skills",
    "session_output",
    "tools",
}


REAL_HE_EVALUATOR_TOOL = r'''#!/usr/bin/env python3
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
'''


def _copy_tree_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def _safe_relative_paths(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def _build_manifest(root: Path) -> list[dict[str, str]]:
    manifest = []
    for relative_path in _safe_relative_paths(root):
        path = root / relative_path
        manifest.append({"path": relative_path, "sha256": sha256_file(path)})
    return manifest


def prepare_isolated_cloud_session_handoff(
    bundle_dir: str | Path = "cloud_session_bundle",
    skill_dir: str | Path = "skills/privacy_expense_cloud_reasoner",
    handoff_dir: str | Path = "cloud_session_handoff",
    artifact_dir: str | Path = "demo_artifacts/04_reasoner",
) -> dict[str, object]:
    bundle_root = Path(bundle_dir)
    skill_root = Path(skill_dir)
    handoff_root = Path(handoff_dir)
    artifact_root = Path(artifact_dir)

    handoff_root.mkdir(parents=True, exist_ok=True)
    session_output_root = handoff_root / "session_output"
    if session_output_root.exists():
        shutil.rmtree(session_output_root)
    session_output_root.mkdir(parents=True, exist_ok=True)

    _copy_tree_contents(bundle_root, handoff_root / "cloud_session_bundle")
    _copy_tree_contents(skill_root, handoff_root / "skills" / "privacy_expense_cloud_reasoner")
    tools_root = handoff_root / "tools"
    tools_root.mkdir(parents=True, exist_ok=True)
    evaluator_path = tools_root / "run_real_he_eval.py"
    evaluator_path.write_text(REAL_HE_EVALUATOR_TOOL, encoding="utf-8")
    evaluator_path.chmod(0o755)

    write_markdown(
        handoff_root / "README.md",
        "\n".join(
            [
                "# Isolated Cloud Session Handoff",
                "",
                "This directory is the minimal package for a second Codex session that simulates the cloud-side reasoner.",
                "",
                "- It includes only the sanitized bundle, the cloud-side skill, and an output folder.",
                "- It includes a Paillier public-key HE evaluator tool that can operate on ciphertexts without plaintext or private keys.",
                "- It must not be given access to the local vault, local secrets, raw source text, or the rest of the repository.",
                "- The second session should write its final JSON to `session_output/cloud_skill_output.json`.",
            ]
        ),
    )
    write_markdown(
        handoff_root / "OPEN_IN_SECOND_SESSION.md",
        "\n".join(
            [
                "# Second Session Instructions",
                "",
                "Open a new Codex session rooted in this directory only.",
                "",
                "Your task is to act as the isolated cloud-side reasoner for a privacy-preserving expense review demo.",
                "",
                "## Files You May Read",
                "",
                "- `cloud_session_bundle/sanitized_request.json`",
                "- `cloud_session_bundle/placeholder_metadata.json`",
                "- `cloud_session_bundle/policy_public_summary.json`",
                "- `cloud_session_bundle/he_public_key.json`",
                "- `cloud_session_bundle/he_ciphertexts.json`",
                "- `cloud_session_bundle/he_policy_operands.json`",
                "- `skills/privacy_expense_cloud_reasoner/SKILL.md`",
                "- `skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json`",
                "- `skills/privacy_expense_cloud_reasoner/schemas/cloud_reasoner_response.schema.json`",
                "- `tools/run_real_he_eval.py`",
                "",
                "## Hard Restrictions",
                "",
                "- Do not ask for raw values.",
                "- Do not ask for decrypt, reveal, lookup_vault, print_raw, or any plaintext recovery action.",
                "- Do not invent numeric values behind placeholders.",
                "- Do not read or reference files outside this directory.",
                "- Do not fabricate HE results. You must run `tools/run_real_he_eval.py` to produce encrypted results.",
                "",
                "## Required Output",
                "",
                "First write an HE call plan to `session_output/he_call_plan.json`.",
                "",
                "Then run:",
                "",
                "```bash",
                "python3 tools/run_real_he_eval.py --plan session_output/he_call_plan.json --output session_output/cloud_skill_output.json",
                "```",
                "",
                "The final JSON file must be `session_output/cloud_skill_output.json`.",
                "",
                "- The JSON must match `skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json`.",
                "- The JSON must include `he_evaluation` produced by the Paillier HE evaluator tool.",
                "- Use only placeholder handles and public policy keys.",
                "- If metadata is insufficient, return `needs_human_review` with an empty `requested_he_ops` array.",
            ]
        ),
    )
    write_markdown(
        session_output_root / "README.md",
        "\n".join(
            [
                "# Session Output",
                "",
                "The isolated cloud-side session should write one file here:",
                "",
                "- `cloud_skill_output.json`",
                "",
                "Intermediate plan files such as `he_call_plan.json` are allowed.",
            ]
        ),
    )

    manifest = _build_manifest(handoff_root)
    write_json(handoff_root / "handoff_manifest.json", manifest)

    disallowed_entries = []
    for path in handoff_root.iterdir():
        if path.name not in ALLOWED_TOP_LEVEL_PATHS:
            disallowed_entries.append(path.name)

    report = {
        "handoff_dir": str(handoff_root),
        "top_level_entries": sorted(path.name for path in handoff_root.iterdir()),
        "disallowed_entries": disallowed_entries,
        "manifest_entries": len(manifest),
        "passed": len(disallowed_entries) == 0,
    }
    write_json(artifact_root / "cloud_session_handoff_manifest.json", manifest)
    write_json(artifact_root / "cloud_session_handoff_report.json", report)
    write_markdown(
        artifact_root / "manual_cloud_session_operator_guide.md",
        "\n".join(
            [
                "# Manual Cloud Session Operator Guide",
                "",
                "1. For the repository-internal baseline handoff, run `scripts/export_cloud_session_bundle.py --prepare-handoff`; for the manual Codex-session path, run `scripts/prepare_real_cloud_session.py --sample-id 0 --device auto`.",
                "2. Open a second Codex session rooted at the generated handoff directory only: `cloud_session_handoff/` for the baseline package, or `real_cloud_session/handoff/` for the manual-session package.",
                "3. In the second session, follow `OPEN_IN_SECOND_SESSION.md`, write `session_output/he_call_plan.json`, and run `python3 tools/run_real_he_eval.py --plan session_output/he_call_plan.json --output session_output/cloud_skill_output.json`.",
                "4. Return to the main repository. For the baseline handoff, run `scripts/import_cloud_he_plan.py --plan cloud_session_handoff/session_output/cloud_skill_output.json` and then `scripts/run_he_ops_demo.py --sample-id 0`.",
                "5. For the manual Codex-session path, run `scripts/import_real_cloud_he_plan.py --plan real_cloud_session/handoff/session_output/cloud_skill_output.json` and then `scripts/run_real_cloud_he_ops_demo.py --sample-id 0`.",
                "6. Review the dedicated Streamlit pages and keep baseline artifacts separate from manual-session artifacts.",
            ]
        ),
    )
    return {"manifest": manifest, "report": report}
