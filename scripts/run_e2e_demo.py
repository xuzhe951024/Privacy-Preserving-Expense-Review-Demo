from __future__ import annotations

import argparse

from src.demo_workflow import run_demo_flow
from src.pipeline import load_samples_from_truth, select_sample, write_showcase_docs
from src.synthetic_data import generate_samples, save_dataset


def ensure_samples() -> list:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full privacy-preserving expense review demo.")
    parser.add_argument("--sample-id", default="0")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    samples = ensure_samples()
    sample = select_sample(samples, args.sample_id)
    result = run_demo_flow(sample, threshold=args.threshold, device=args.device)
    write_showcase_docs(".")
    print(f"Completed E2E demo for {sample.sample_id}. Final decision: {result['reassembly']['actual_final_decision']}")


if __name__ == "__main__":
    main()

