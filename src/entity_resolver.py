from __future__ import annotations

from src.models import DetectedEntity

SOURCE_PRIORITY = {
    "rule": 30,
    "gliner_native": 20,
    "gliner_heuristic": 10,
}

LABEL_PRIORITY = {
    "EMAIL": 40,
    "PHONE_NUMBER": 39,
    "EMPLOYEE_ID": 38,
    "INVOICE_ID": 37,
    "PROJECT_CODE": 36,
    "COST_CENTER": 35,
    "CARD_LAST4": 34,
    "AMOUNT": 33,
    "DATE": 32,
    "PERSON": 20,
    "VENDOR": 15,
}


def _overlaps(left: DetectedEntity, right: DetectedEntity) -> bool:
    return left.start < right.end and right.start < left.end


def _rank(entity: DetectedEntity) -> tuple[int, int, float, int]:
    return (
        SOURCE_PRIORITY.get(entity.source, 0),
        LABEL_PRIORITY.get(entity.label, 0),
        entity.score,
        entity.end - entity.start,
    )


def _prefer(left: DetectedEntity, right: DetectedEntity) -> DetectedEntity:
    return left if _rank(left) >= _rank(right) else right


def resolve_entities(rule_entities: list[DetectedEntity], gliner_entities: list[DetectedEntity]) -> list[DetectedEntity]:
    resolved: list[DetectedEntity] = []
    for candidate in sorted(rule_entities + gliner_entities, key=lambda item: (item.start, item.end, -_rank(item)[0])):
        replaced_index = None
        keep_candidate = True
        for index, existing in enumerate(resolved):
            if not _overlaps(existing, candidate):
                continue
            preferred = _prefer(existing, candidate)
            if preferred is existing:
                keep_candidate = False
            else:
                replaced_index = index
            break
        if keep_candidate:
            if replaced_index is not None:
                resolved[replaced_index] = candidate
            else:
                resolved.append(candidate)
    return sorted(resolved, key=lambda item: (item.start, item.end, item.label))

