from __future__ import annotations

import argparse
from statistics import mean

from src.demo_workflow import detect_sample
from src.eval_metrics import summarize_detection
from src.pipeline import load_samples_from_truth, write_showcase_docs
from src.report_writer import write_csv, write_json, write_jsonl
from src.synthetic_data import generate_samples, save_dataset


def ensure_samples() -> list:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def aggregate_macro_f1(metrics: list[dict[str, object]], key: str) -> float:
    values = [float(row[key]) for row in metrics]
    return round(mean(values), 4) if values else 0.0


def run_threshold_summary(samples: list, threshold: float, device: str) -> dict[str, object]:
    truth_records = [sample.truth_record() for sample in samples]
    prediction_records = []
    for sample in samples:
        detection = detect_sample(sample, threshold=threshold, device=device)
        prediction_records.append(
            {
                "sample_id": sample.sample_id,
                "predictions": [entity.to_dict() for entity in detection["resolved_entities"]],
            }
        )
    summary = summarize_detection(truth_records, prediction_records)
    return {
        "threshold": threshold,
        "macro_exact_f1": aggregate_macro_f1(summary["metrics_by_entity"], "exact_f1"),
        "macro_relaxed_f1": aggregate_macro_f1(summary["metrics_by_entity"], "relaxed_f1"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate detection quality.")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    samples = ensure_samples()
    truth_records = [sample.truth_record() for sample in samples]
    prediction_records = []
    detector_status_rows = []
    for sample in samples:
        detection = detect_sample(sample, threshold=args.threshold, device=args.device)
        prediction_records.append(
            {
                "sample_id": sample.sample_id,
                "predictions": [entity.to_dict() for entity in detection["resolved_entities"]],
            }
        )
        detector_status_rows.append({"sample_id": sample.sample_id, **detection["gliner_status"]})

    summary = summarize_detection(truth_records, prediction_records)
    threshold_rows = [run_threshold_summary(samples, threshold, args.device) for threshold in [0.2, 0.3, 0.35, 0.5]]

    write_json(
        "demo_artifacts/02_detection/detection_samples.json",
        {
            "samples": summary["sample_summaries"][:25],
            "gliner_status": detector_status_rows[:25],
        },
    )
    write_csv("demo_artifacts/02_detection/detection_table.csv", summary["detection_rows"])
    write_csv("demo_artifacts/02_detection/detection_metrics_by_entity.csv", summary["metrics_by_entity"])
    write_csv("demo_artifacts/02_detection/threshold_sweep.csv", threshold_rows)
    write_csv("demo_artifacts/02_detection/entity_confusion_matrix.csv", summary["confusion_rows"])
    write_jsonl("demo_artifacts/02_detection/missed_entities.jsonl", summary["missed_entities"])
    write_jsonl("demo_artifacts/02_detection/boundary_errors.jsonl", summary["boundary_errors"])
    write_showcase_docs(".")
    print("Detection evaluation artifacts written to demo_artifacts/02_detection.")


if __name__ == "__main__":
    main()

