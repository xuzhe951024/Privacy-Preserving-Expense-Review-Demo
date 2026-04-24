from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.models import DetectedEntity
from src.policy import get_entity_policy


HEURISTIC_PATTERNS = [
    ("PERSON", re.compile(r"\b(?:Employee|Traveler|reviewer contact:|follow-up summary for)\s+([A-Z][a-z]+ [A-Z][a-z]+)"), 0.64),
    ("PERSON", re.compile(r'"employee"\s*:\s*"([A-Z][a-z]+ [A-Z][a-z]+)"'), 0.62),
    (
        "VENDOR",
        re.compile(
            r"\b(?:vendor|hotel|carrier|with|from|at)\s+([A-Z][A-Za-z0-9&' .-]{2,40}?)(?=[,.;]| charged| on | dated| issued|\.|$)",
            re.IGNORECASE,
        ),
        0.56,
    ),
]


@dataclass(slots=True)
class DetectorRun:
    entities: list[DetectedEntity]
    model_status: str
    detail: str


def _heuristic_detect(text: str, threshold: float) -> list[DetectedEntity]:
    entities: list[DetectedEntity] = []
    for label, pattern, score in HEURISTIC_PATTERNS:
        if score < threshold:
            continue
        for match_index, match in enumerate(pattern.finditer(text), start=1):
            value = match.group(1).strip()
            start = match.start(1)
            end = match.end(1)
            policy = get_entity_policy(label)
            entities.append(
                DetectedEntity(
                    entity_id=f"heuristic_{label.lower()}_{match_index}",
                    label=label,
                    text=value,
                    start=start,
                    end=end,
                    score=score,
                    source="gliner_heuristic",
                    normalized_value=value,
                    expected_action=policy.get("action", "tokenize_encrypt"),
                    sensitivity_level="medium" if label == "VENDOR" else "high",
                )
            )
    return entities


def _native_gliner_detect(text: str, threshold: float, device: str) -> DetectorRun:
    try:
        from gliner import GLiNER  # type: ignore
    except Exception as exc:  # pragma: no cover - import path is environment-specific
        return DetectorRun([], "degraded", f"GLiNER import unavailable: {exc}")

    try:
        model = GLiNER.from_pretrained("nvidia/gliner-PII")
        predictions = model.predict_entities(text, ["person", "organization"], threshold=threshold)
    except Exception as exc:  # pragma: no cover - model load is environment-specific
        return DetectorRun([], "degraded", f"GLiNER model load failed: {exc}")

    label_map = {"person": "PERSON", "organization": "VENDOR"}
    entities: list[DetectedEntity] = []
    for index, prediction in enumerate(predictions, start=1):
        mapped_label = label_map.get(prediction["label"].lower())
        if mapped_label is None:
            continue
        policy = get_entity_policy(mapped_label)
        entities.append(
            DetectedEntity(
                entity_id=f"gliner_{mapped_label.lower()}_{index}",
                label=mapped_label,
                text=prediction["text"],
                start=prediction["start"],
                end=prediction["end"],
                score=float(prediction["score"]),
                source="gliner_native",
                normalized_value=prediction["text"],
                expected_action=policy.get("action", "tokenize_encrypt"),
                sensitivity_level="medium" if mapped_label == "VENDOR" else "high",
            )
        )
    return DetectorRun(entities, "native", f"GLiNER native inference on device={device}")


def detect_gliner_entities(text: str, threshold: float = 0.3, device: str = "auto") -> DetectorRun:
    native_result = _native_gliner_detect(text, threshold=threshold, device=device)
    if native_result.model_status == "native":
        return native_result
    heuristic_entities = _heuristic_detect(text, threshold=threshold)
    detail = native_result.detail if native_result.detail else "GLiNER heuristic fallback"
    if heuristic_entities:
        detail = f"{detail}; heuristic fallback active"
    return DetectorRun(heuristic_entities, "degraded", detail)


def detector_status_report(run: DetectorRun) -> dict[str, Any]:
    return {
        "model_status": run.model_status,
        "detail": run.detail,
        "entity_count": len(run.entities),
    }
