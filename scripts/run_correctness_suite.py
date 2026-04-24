from __future__ import annotations

import argparse
from statistics import mean

from src.demo_workflow import detect_sample, run_demo_flow
from src.eval_metrics import summarize_detection
from src.pipeline import load_samples_from_truth, write_showcase_docs
from src.report_writer import write_csv, write_json, write_markdown
from src.synthetic_data import build_edge_case_matrix, generate_samples, save_dataset


def entity_metric_line(metric_row: dict[str, object]) -> str:
    return (
        f"- {metric_row['label']}: exact F1={metric_row['exact_f1']}, "
        f"relaxed F1={metric_row['relaxed_f1']}, false_positive_rate={metric_row['false_positive_rate']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the demo correctness suite.")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    samples = generate_samples(args.n, args.seed)
    save_dataset(samples, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")

    truth_records = [sample.truth_record() for sample in samples]
    prediction_records = []
    for sample in samples:
        detection = detect_sample(sample, threshold=args.threshold, device=args.device)
        prediction_records.append({"sample_id": sample.sample_id, "predictions": [entity.to_dict() for entity in detection["resolved_entities"]]})
    detection_summary = summarize_detection(truth_records, prediction_records)

    replacement_passes = 0
    policy_passes = 0
    final_passes = 0
    leakage_count = 0
    audit_complete = 0
    failures = []
    for sample in load_samples_from_truth("data/synthetic_ground_truth.jsonl"):
        result = run_demo_flow(sample, threshold=args.threshold, device=args.device)
        replacement_ok = result["sanitized_payload"].replacement_report["token_vault_count_match"] and result["sanitized_payload"].leakage_check["passed"]
        policy_ok = bool(result["reassembly"]["policy_ops_correctness"]["passed"])
        final_ok = bool(result["reassembly"]["final_decision_correctness"]["passed"])
        audit_stages = {event.stage for event in result["audit_logger"].events}
        audit_ok = {"detect", "sanitize", "request", "reason", "local_ops", "reassembly"} <= audit_stages

        replacement_passes += int(replacement_ok)
        policy_passes += int(policy_ok)
        final_passes += int(final_ok)
        leakage_count += int(result["sanitized_payload"].leakage_check["raw_value_leakage_count"])
        leakage_count += len(result["bundle_export"]["report"]["raw_value_hits"])
        audit_complete += int(audit_ok)

        if not (replacement_ok and policy_ok and final_ok and audit_ok):
            failures.append(
                {
                    "sample_id": sample.sample_id,
                    "replacement_ok": replacement_ok,
                    "policy_ok": policy_ok,
                    "final_ok": final_ok,
                    "audit_ok": audit_ok,
                    "expected_final_decision": sample.expected_final_decision,
                    "actual_final_decision": result["reassembly"]["actual_final_decision"],
                }
            )

    total = len(samples)
    replacement_accuracy = round(replacement_passes / total, 4)
    policy_accuracy = round(policy_passes / total, 4)
    final_accuracy = round(final_passes / total, 4)
    audit_accuracy = round(audit_complete / total, 4)
    macro_exact_f1 = round(mean(float(row["exact_f1"]) for row in detection_summary["metrics_by_entity"]), 4)
    macro_relaxed_f1 = round(mean(float(row["relaxed_f1"]) for row in detection_summary["metrics_by_entity"]), 4)

    status = "PASS"
    if leakage_count != 0 or replacement_accuracy != 1.0 or policy_accuracy != 1.0 or final_accuracy != 1.0 or audit_accuracy != 1.0:
        status = "FAIL"

    summary = {
        "status": status,
        "dataset_size": total,
        "macro_exact_f1": macro_exact_f1,
        "macro_relaxed_f1": macro_relaxed_f1,
        "replacement_accuracy": replacement_accuracy,
        "policy_accuracy": policy_accuracy,
        "final_accuracy": final_accuracy,
        "raw_leakage_count": leakage_count,
        "audit_completeness": audit_accuracy,
        "failed_samples": failures,
    }

    write_csv("demo_artifacts/09_validation/edge_case_matrix.csv", build_edge_case_matrix())
    write_json("demo_artifacts/09_validation/test_run_summary.json", summary)
    write_markdown(
        "demo_artifacts/09_validation/result_correctness_summary.md",
        "\n".join(
            [
                f"STATUS: {status}",
                "",
                "# Result Correctness Summary",
                "",
                f"- Dataset size: {total}",
                f"- Macro exact span F1: {macro_exact_f1}",
                f"- Macro relaxed span F1: {macro_relaxed_f1}",
                f"- Replacement correctness: {replacement_accuracy}",
                f"- Policy ops correctness: {policy_accuracy}",
                f"- Final decision accuracy: {final_accuracy}",
                f"- Raw leakage count: {leakage_count}",
                f"- Audit completeness: {audit_accuracy}",
                "",
                "## Entity Metrics",
                "",
                *[entity_metric_line(row) for row in detection_summary["metrics_by_entity"]],
                "",
                "## Failure Samples",
                "",
                *(["- None"] if not failures else [f"- {failure['sample_id']}: expected={failure['expected_final_decision']}, actual={failure['actual_final_decision']}" for failure in failures[:20]]),
                "",
                "## Current Boundaries",
                "",
                "- The default detector uses rules plus a GLiNER-compatible fallback heuristic unless the GLiNER model is available.",
                "- Real TFHE-rs execution is intentionally out of scope for the default path.",
                "- Ambiguous malformed values are routed to human review rather than guessed.",
            ]
        ),
    )
    write_showcase_docs(".")
    print(f"Correctness suite completed with status {status}.")


if __name__ == "__main__":
    main()

