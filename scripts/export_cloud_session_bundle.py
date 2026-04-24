from __future__ import annotations

import argparse

from src.cloud_bundle_exporter import export_cloud_bundle
from src.cloud_session_handoff import prepare_isolated_cloud_session_handoff
from src.demo_workflow import detect_sample
from src.pipeline import load_samples_from_truth, select_sample, write_showcase_docs
from src.sanitizer import sanitize_sample
from src.synthetic_data import generate_samples, save_dataset
from src.vault import Vault


def ensure_samples() -> list:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a sanitized cloud session bundle.")
    parser.add_argument("--sample-id", default="0")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--prepare-handoff", action="store_true")
    args = parser.parse_args()

    samples = ensure_samples()
    sample = select_sample(samples, args.sample_id)
    detection = detect_sample(sample, threshold=args.threshold, device=args.device)
    vault = Vault()
    sanitized_payload = sanitize_sample(sample, detection["resolved_entities"], vault)
    export_cloud_bundle(sanitized_payload, sample, vault=vault)
    if args.prepare_handoff:
        prepare_isolated_cloud_session_handoff()
    write_showcase_docs(".")
    if args.prepare_handoff:
        print(f"Exported cloud session bundle and isolated handoff package for {sample.sample_id}.")
    else:
        print(f"Exported cloud session bundle for {sample.sample_id}.")


if __name__ == "__main__":
    main()
