from __future__ import annotations

from src.demo_workflow import run_demo_flow
from src.synthetic_data import generate_samples, save_dataset


def main() -> None:
    samples = generate_samples(4, 42)
    save_dataset(samples, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    result = run_demo_flow(samples[0])
    print(f"Smoke test passed for {samples[0].sample_id}: {result['reassembly']['actual_final_decision']}")


if __name__ == "__main__":
    main()

