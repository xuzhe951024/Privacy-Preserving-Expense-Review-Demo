from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.demo_workflow import run_demo_flow
from src.pipeline import load_samples_from_truth, select_sample
from src.report_writer import write_json, write_markdown
from src.synthetic_data import generate_samples, save_dataset
from src.vault import Vault


def ensure_samples() -> list:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def candidate_strings(entity: dict) -> list[str]:
    values = [entity["text"]]
    if entity.get("normalized_value"):
        values.append(entity["normalized_value"])
        if entity["label"] == "AMOUNT":
            values.append(entity["normalized_value"].replace(".", ""))
    return [value for value in values if value]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check that cloud-facing payloads do not leak raw values.")
    parser.add_argument("--sample-id", default="0")
    args = parser.parse_args()

    samples = ensure_samples()
    sample = select_sample(samples, args.sample_id)
    if not Path("demo_artifacts/03_sanitization/sanitized_payload_examples.json").exists():
        run_demo_flow(sample)

    sanitized_payload = load_json("demo_artifacts/03_sanitization/sanitized_payload_examples.json")
    cloud_request = load_json("demo_artifacts/04_reasoner/cloud_request_mock.json")
    bundle_files = {
        path.name: path.read_text(encoding="utf-8")
        for path in Path("cloud_session_bundle").glob("*")
        if path.is_file()
    }
    artifact_blobs = {
        "sanitized_payload_examples.json": json.dumps(sanitized_payload),
        "cloud_request_mock.json": json.dumps(cloud_request),
        **bundle_files,
    }
    leakage_hits = []
    for entity in sample.truth_record()["entities"]:
        for candidate in candidate_strings(entity):
            for file_name, blob in artifact_blobs.items():
                if candidate and candidate in blob:
                    leakage_hits.append({"file": file_name, "label": entity["label"], "value": candidate})

    vault = Vault()
    token_count = len(sanitized_payload["metadata"])
    roundtrip_success = 0
    for token in sanitized_payload["metadata"]:
        try:
            vault.get_secret(sanitized_payload["session_id"], token)
            roundtrip_success += 1
        except Exception:
            continue
    vault_roundtrip_accuracy = roundtrip_success / token_count if token_count else 1.0

    minimal_payload = {
        "sample_id": sanitized_payload["sample_id"],
        "sanitized_text": sanitized_payload["sanitized_text"],
        "public_context": {
            "expense_type": sanitized_payload["public_context"].get("expense_type"),
            "policy_key": sanitized_payload["public_context"].get("policy_key"),
            "receipt_attached": sanitized_payload["public_context"].get("receipt_attached"),
        },
        "metadata": {token: {"entity_type": value["entity_type"]} for token, value in sanitized_payload["metadata"].items()},
    }
    write_markdown(
        "demo_artifacts/06_security/minimal_context_comparison.md",
        "\n".join(
            [
                "# Minimal Context Comparison",
                "",
                "## Standard sanitized payload",
                "",
                "```json",
                json.dumps(
                    {
                        "sanitized_text": sanitized_payload["sanitized_text"],
                        "public_context": sanitized_payload["public_context"],
                        "metadata_keys": list(sanitized_payload["metadata"]),
                    },
                    indent=2,
                ),
                "```",
                "",
                "## Minimal payload",
                "",
                "```json",
                json.dumps(minimal_payload, indent=2),
                "```",
                "",
                "The minimal payload removes scores, sources, and detailed allowed-op metadata. This reduces context but can increase the chance of human review because the cloud reasoner has less routing context.",
            ]
        ),
    )
    report = {
        "sample_id": sample.sample_id,
        "cloud_request_raw_value_leakage": len(leakage_hits),
        "leakage_hits": leakage_hits,
        "vault_roundtrip_accuracy": vault_roundtrip_accuracy,
        "passed": len(leakage_hits) == 0 and vault_roundtrip_accuracy == 1.0,
    }
    write_json("demo_artifacts/06_security/leakage_report.json", report)
    print(f"Leakage report written. Passed={report['passed']}")


if __name__ == "__main__":
    main()

