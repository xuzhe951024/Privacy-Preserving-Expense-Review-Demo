from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from src.models import DetectedEntity
from src.policy import get_entity_policy


PATTERN_SPECS = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE_NUMBER", re.compile(r"\+1-\d{3}-\d{3}-\d{4}\b")),
    ("EMPLOYEE_ID", re.compile(r"\bE-\d{4,6}\b")),
    ("INVOICE_ID", re.compile(r"\bINV-\d{4}-\d{4}\b")),
    ("PROJECT_CODE", re.compile(r"\bPC-[A-Z]+-\d{3}\b")),
    ("COST_CENTER", re.compile(r"\bCC-\d{3,4}\b")),
    ("CARD_LAST4", re.compile(r"(?<=card ending )\d{4}\b")),
    ("AMOUNT", re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b")),
    ("DATE", re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")),
]

VENDOR_CONTEXT_PATTERNS = [
    re.compile(r"\bVendor (?P<value>[A-Z][A-Za-z0-9&'-]*(?:\s+[A-Z0-9][A-Za-z0-9&'-]*){0,4})(?=\s+charged\b)"),
    re.compile(r"\bat vendor (?P<value>[A-Z][A-Za-z0-9&'-]*(?:\s+[A-Z0-9][A-Za-z0-9&'-]*){0,4})(?=[,.;]|\s+for\b|\s+with\b|$)"),
]


def normalize_value(label: str, value: str) -> str:
    if label == "AMOUNT":
        return value.replace("$", "").replace(",", "")
    if label == "PHONE_NUMBER":
        return "".join(filter(str.isdigit, value))
    if label == "DATE":
        return str((date.fromisoformat(value) - date(1970, 1, 1)).days)
    return value


def detect_rule_entities(text: str) -> list[DetectedEntity]:
    entities: list[DetectedEntity] = []
    for label, pattern in PATTERN_SPECS:
        for match_index, match in enumerate(pattern.finditer(text), start=1):
            value = match.group(0)
            policy = get_entity_policy(label)
            entities.append(
                DetectedEntity(
                    entity_id=f"rule_{label.lower()}_{match_index}",
                    label=label,
                    text=value,
                    start=match.start(),
                    end=match.end(),
                    score=0.99,
                    source="rule",
                    normalized_value=normalize_value(label, value),
                    expected_action=policy.get("action", "tokenize_encrypt"),
                )
            )
    vendor_policy = get_entity_policy("VENDOR")
    for pattern_index, pattern in enumerate(VENDOR_CONTEXT_PATTERNS, start=1):
        for match_index, match in enumerate(pattern.finditer(text), start=1):
            value = match.group("value")
            start = match.start("value")
            end = match.end("value")
            entities.append(
                DetectedEntity(
                    entity_id=f"rule_vendor_{pattern_index}_{match_index}",
                    label="VENDOR",
                    text=value,
                    start=start,
                    end=end,
                    score=0.97,
                    source="rule",
                    normalized_value=value,
                    sensitivity_level="medium",
                    expected_action=vendor_policy.get("action", "tokenize_encrypt"),
                )
            )
    return sorted(entities, key=lambda item: (item.start, item.end, item.label))


def strong_format_labels() -> Iterable[str]:
    return {label for label, _pattern in PATTERN_SPECS}
