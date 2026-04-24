from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from src.models import DetectedEntity
from src.policy import get_entity_policy
from src.runtime_env import ensure_local_runtime_dirs, resolve_runtime_device


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


def _move_model_to_device(model: object, device: str) -> object:
    if hasattr(model, "to"):
        moved = model.to(device)
        if moved is not None:
            model = moved
    if hasattr(model, "eval"):
        model.eval()
    return model


@lru_cache(maxsize=4)
def _load_native_model(model_name: str, device: str) -> object:
    ensure_local_runtime_dirs(".")
    from gliner import GLiNER  # type: ignore

    model = GLiNER.from_pretrained(model_name)
    return _move_model_to_device(model, device)


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
    runtime = resolve_runtime_device(device)
    resolved_device = runtime["resolved_device"]

    try:
        from gliner import GLiNER  # type: ignore  # noqa: F401
    except Exception as exc:  # pragma: no cover - import path is environment-specific
        return DetectorRun([], "degraded", f"GLiNER import unavailable: {exc}")

    try:
        model = _load_native_model("nvidia/gliner-PII", resolved_device)
        predictions = model.predict_entities(text, ["person", "organization"], threshold=threshold)
    except Exception as exc:  # pragma: no cover - model load is environment-specific
        if resolved_device != "cpu":
            try:
                model = _load_native_model("nvidia/gliner-PII", "cpu")
                predictions = model.predict_entities(text, ["person", "organization"], threshold=threshold)
                detail = (
                    f"GLiNER GPU path failed on device={resolved_device}: {exc}. "
                    "Fell back to CPU inference."
                )
                return _predictions_to_run(predictions, detail, resolved_device="cpu")
            except Exception as cpu_exc:
                return DetectorRun(
                    [],
                    "degraded",
                    (
                        f"GLiNER model load failed on device={resolved_device}: {exc}. "
                        f"CPU fallback also failed: {cpu_exc}"
                    ),
                )
        return DetectorRun([], "degraded", f"GLiNER model load failed on device={resolved_device}: {exc}")

    detail = (
        f"GLiNER native inference on requested_device={device}, resolved_device={resolved_device}. "
        f"{runtime['reason']}"
    )
    if runtime["device_names"]:
        detail += f" GPU={runtime['device_names'][0]}"
    return _predictions_to_run(predictions, detail, resolved_device=resolved_device)


def _predictions_to_run(predictions: list[dict[str, Any]], detail: str, resolved_device: str) -> DetectorRun:
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
    model_status = "native_gpu" if resolved_device.startswith("cuda") else "native_cpu"
    return DetectorRun(entities, model_status, detail)


def detect_gliner_entities(text: str, threshold: float = 0.3, device: str = "auto") -> DetectorRun:
    native_result = _native_gliner_detect(text, threshold=threshold, device=device)
    if native_result.model_status in {"native_gpu", "native_cpu"}:
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
