from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class DetectedEntity:
    label: str
    text: str
    start: int
    end: int
    entity_id: str | None = None
    score: float = 1.0
    source: str = "rule"
    normalized_value: str | None = None
    sensitivity_level: str = "high"
    expected_action: str = "tokenize_encrypt"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExpenseSample:
    sample_id: str
    raw_text: str
    entities: list[DetectedEntity]
    expected_policy_ops: list[dict[str, Any]]
    expected_final_decision: str
    expected_missing_items: list[str]
    edge_case_tags: list[str]
    workflow_context: dict[str, Any] = field(default_factory=dict)

    def raw_record(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "raw_text": self.raw_text,
            "workflow_context": self.workflow_context,
            "edge_case_tags": self.edge_case_tags,
        }

    def truth_record(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "raw_text": self.raw_text,
            "entities": [entity.to_dict() for entity in self.entities],
            "expected_policy_ops": self.expected_policy_ops,
            "expected_final_decision": self.expected_final_decision,
            "expected_missing_items": self.expected_missing_items,
            "edge_case_tags": self.edge_case_tags,
            "workflow_context": self.workflow_context,
        }

    @classmethod
    def from_truth_record(cls, record: dict[str, Any]) -> "ExpenseSample":
        return cls(
            sample_id=record["sample_id"],
            raw_text=record["raw_text"],
            entities=[DetectedEntity(**entity) for entity in record["entities"]],
            expected_policy_ops=record.get("expected_policy_ops", []),
            expected_final_decision=record["expected_final_decision"],
            expected_missing_items=record.get("expected_missing_items", []),
            edge_case_tags=record.get("edge_case_tags", []),
            workflow_context=record.get("workflow_context", {}),
        )


@dataclass(slots=True)
class SanitizedPayload:
    sample_id: str
    session_id: str
    sanitized_text: str
    metadata: dict[str, dict[str, Any]]
    policy_summary: dict[str, Any]
    public_context: dict[str, Any]
    replacement_report: dict[str, Any]
    leakage_check: dict[str, Any]
    token_preview: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditEvent:
    timestamp: str
    stage: str
    action: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

