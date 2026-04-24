from __future__ import annotations

from src.entity_resolver import resolve_entities
from src.models import DetectedEntity


def test_overlap_resolution_prefers_email_over_nested_person():
    email = "john.miller@corp.example"
    rule_entities = [
        DetectedEntity(label="EMAIL", text=email, start=0, end=len(email), source="rule", score=0.99),
    ]
    gliner_entities = [
        DetectedEntity(label="PERSON", text="John Miller", start=0, end=11, source="gliner_heuristic", score=0.7),
    ]
    resolved = resolve_entities(rule_entities, gliner_entities)
    assert len(resolved) == 1
    assert resolved[0].label == "EMAIL"

