from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.models import DetectedEntity


def exact_match(prediction: DetectedEntity, truth: DetectedEntity) -> bool:
    return (
        prediction.label == truth.label
        and prediction.start == truth.start
        and prediction.end == truth.end
        and prediction.text == truth.text
    )


def relaxed_match(prediction: DetectedEntity, truth: DetectedEntity) -> bool:
    return prediction.label == truth.label and prediction.start < truth.end and truth.start < prediction.end


def greedy_match(
    truths: list[DetectedEntity],
    predictions: list[DetectedEntity],
    relaxed: bool,
) -> tuple[list[tuple[DetectedEntity, DetectedEntity]], list[DetectedEntity], list[DetectedEntity]]:
    matcher = relaxed_match if relaxed else exact_match
    matched_truth_indexes: set[int] = set()
    matched_prediction_indexes: set[int] = set()
    pairs: list[tuple[DetectedEntity, DetectedEntity]] = []
    for prediction_index, prediction in enumerate(predictions):
        for truth_index, truth in enumerate(truths):
            if truth_index in matched_truth_indexes:
                continue
            if matcher(prediction, truth):
                matched_truth_indexes.add(truth_index)
                matched_prediction_indexes.add(prediction_index)
                pairs.append((prediction, truth))
                break
    missed_truths = [truth for index, truth in enumerate(truths) if index not in matched_truth_indexes]
    missed_predictions = [prediction for index, prediction in enumerate(predictions) if index not in matched_prediction_indexes]
    return pairs, missed_truths, missed_predictions


def _metric(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def summarize_detection(
    truth_records: list[dict[str, Any]],
    prediction_records: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "truth": 0, "pred": 0})
    relaxed_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    confusion_matrix: dict[tuple[str, str], int] = defaultdict(int)
    missed_entities: list[dict[str, Any]] = []
    boundary_errors: list[dict[str, Any]] = []
    detection_rows: list[dict[str, Any]] = []
    sample_summaries: list[dict[str, Any]] = []

    for truth_record, prediction_record in zip(truth_records, prediction_records):
        truths = [DetectedEntity(**entity) for entity in truth_record["entities"]]
        predictions = [DetectedEntity(**entity) for entity in prediction_record["predictions"]]
        exact_pairs, exact_missed_truths, exact_missed_predictions = greedy_match(truths, predictions, relaxed=False)
        relaxed_pairs, relaxed_missed_truths, relaxed_missed_predictions = greedy_match(truths, predictions, relaxed=True)

        for truth in truths:
            exact_counts[truth.label]["truth"] += 1
        for prediction in predictions:
            exact_counts[prediction.label]["pred"] += 1

        for prediction, truth in exact_pairs:
            exact_counts[truth.label]["tp"] += 1
            confusion_matrix[(truth.label, prediction.label)] += 1
            detection_rows.append(
                {
                    "sample_id": truth_record["sample_id"],
                    "text": prediction.text,
                    "label": prediction.label,
                    "start": prediction.start,
                    "end": prediction.end,
                    "score": prediction.score,
                    "source": prediction.source,
                    "match_type": "exact",
                }
            )

        for truth in exact_missed_truths:
            exact_counts[truth.label]["fn"] += 1
            missed_entities.append({"sample_id": truth_record["sample_id"], **truth.to_dict()})
            confusion_matrix[(truth.label, "MISS")] += 1

        for prediction in exact_missed_predictions:
            exact_counts[prediction.label]["fp"] += 1
            confusion_matrix[("NONE", prediction.label)] += 1
            detection_rows.append(
                {
                    "sample_id": truth_record["sample_id"],
                    "text": prediction.text,
                    "label": prediction.label,
                    "start": prediction.start,
                    "end": prediction.end,
                    "score": prediction.score,
                    "source": prediction.source,
                    "match_type": "false_positive",
                }
            )

        for prediction, truth in relaxed_pairs:
            relaxed_counts[truth.label]["tp"] += 1
            if not exact_match(prediction, truth):
                boundary_errors.append(
                    {
                        "sample_id": truth_record["sample_id"],
                        "truth": truth.to_dict(),
                        "prediction": prediction.to_dict(),
                    }
                )

        for truth in relaxed_missed_truths:
            relaxed_counts[truth.label]["fn"] += 1
        for prediction in relaxed_missed_predictions:
            relaxed_counts[prediction.label]["fp"] += 1

        sample_summaries.append(
            {
                "sample_id": truth_record["sample_id"],
                "truth_count": len(truths),
                "prediction_count": len(predictions),
                "exact_match_count": len(exact_pairs),
                "relaxed_match_count": len(relaxed_pairs),
                "predictions": [prediction.to_dict() for prediction in predictions],
            }
        )

    metric_rows = []
    labels = sorted(set(exact_counts) | set(relaxed_counts))
    for label in labels:
        exact_precision, exact_recall, exact_f1 = _metric(
            exact_counts[label]["tp"], exact_counts[label]["fp"], exact_counts[label]["fn"]
        )
        relaxed_precision, relaxed_recall, relaxed_f1 = _metric(
            relaxed_counts[label]["tp"], relaxed_counts[label]["fp"], relaxed_counts[label]["fn"]
        )
        metric_rows.append(
            {
                "label": label,
                "exact_precision": round(exact_precision, 4),
                "exact_recall": round(exact_recall, 4),
                "exact_f1": round(exact_f1, 4),
                "relaxed_precision": round(relaxed_precision, 4),
                "relaxed_recall": round(relaxed_recall, 4),
                "relaxed_f1": round(relaxed_f1, 4),
                "false_positive_rate": round(
                    exact_counts[label]["fp"] / exact_counts[label]["pred"] if exact_counts[label]["pred"] else 0.0,
                    4,
                ),
                "truth_count": exact_counts[label]["truth"],
                "prediction_count": exact_counts[label]["pred"],
            }
        )

    confusion_rows = [
        {"truth_label": truth_label, "predicted_label": predicted_label, "count": count}
        for (truth_label, predicted_label), count in sorted(confusion_matrix.items())
    ]
    return {
        "metrics_by_entity": metric_rows,
        "detection_rows": detection_rows,
        "missed_entities": missed_entities,
        "boundary_errors": boundary_errors,
        "confusion_rows": confusion_rows,
        "sample_summaries": sample_summaries,
    }

