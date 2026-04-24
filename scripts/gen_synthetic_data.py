from __future__ import annotations

import argparse

from src.pipeline import write_showcase_docs
from src.report_writer import write_csv
from src.synthetic_data import build_edge_case_matrix, generate_samples, save_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic expense samples and ground truth.")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    samples = generate_samples(args.n, args.seed)
    save_dataset(samples, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    write_csv("demo_artifacts/09_validation/edge_case_matrix.csv", build_edge_case_matrix())
    write_showcase_docs(".")
    print(f"Generated {len(samples)} synthetic samples.")


if __name__ == "__main__":
    main()

