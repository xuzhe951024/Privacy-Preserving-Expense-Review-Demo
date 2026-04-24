from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.audit import AuditLogger
from src.he_service_mock import execute_he_plan
from src.models import SanitizedPayload
from src.pipeline import load_samples_from_truth, select_sample
from src.reassembler import reassemble_results
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute HE mock ops and local reassembly.")
    parser.add_argument("--sample-id", default="0")
    args = parser.parse_args()

    sanitized_payload_path = Path("demo_artifacts/03_sanitization/sanitized_payload_examples.json")
    he_plan_path = Path("demo_artifacts/04_reasoner/he_call_plan.json")
    if not sanitized_payload_path.exists() or not he_plan_path.exists():
        raise SystemExit("Missing sanitized payload or HE plan. Run the E2E flow first.")

    samples = ensure_samples()
    sample = select_sample(samples, args.sample_id)
    payload_dict = load_json(sanitized_payload_path)
    sanitized_payload = SanitizedPayload(
        sample_id=payload_dict["sample_id"],
        session_id=payload_dict["session_id"],
        sanitized_text=payload_dict["sanitized_text"],
        metadata=payload_dict["metadata"],
        policy_summary=payload_dict["policy_summary"],
        public_context=payload_dict["public_context"],
        replacement_report={},
        leakage_check={},
        token_preview=[],
    )
    he_plan = load_json(he_plan_path)
    vault = Vault()
    audit_logger = AuditLogger()
    audit_logger.record("local_ops", "he_plan_reused", sample_id=sample.sample_id, session_id=sanitized_payload.session_id)
    he_results = execute_he_plan(
        he_plan,
        sanitized_payload.session_id,
        vault,
        artifact_dir="demo_artifacts/05_reassembly",
        result_store_dir=".local/he_results",
    )
    reassembly = reassemble_results(
        sample,
        sanitized_payload,
        he_plan,
        he_results,
        audit_logger,
        artifact_dir="demo_artifacts/05_reassembly",
        result_store_dir=".local/he_results",
    )
    print(f"HE demo finished. Final decision: {reassembly['actual_final_decision']}")


if __name__ == "__main__":
    main()

