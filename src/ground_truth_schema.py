from __future__ import annotations


def build_ground_truth_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Synthetic expense review ground truth",
        "type": "object",
        "required": [
            "sample_id",
            "raw_text",
            "entities",
            "expected_policy_ops",
            "expected_final_decision",
            "expected_missing_items",
            "edge_case_tags",
        ],
        "properties": {
            "sample_id": {"type": "string"},
            "raw_text": {"type": "string"},
            "entities": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "label",
                        "text",
                        "start",
                        "end",
                        "normalized_value",
                        "sensitivity_level",
                        "expected_action",
                    ],
                    "properties": {
                        "entity_id": {"type": ["string", "null"]},
                        "label": {"type": "string"},
                        "text": {"type": "string"},
                        "start": {"type": "integer", "minimum": 0},
                        "end": {"type": "integer", "minimum": 0},
                        "score": {"type": "number"},
                        "source": {"type": "string"},
                        "normalized_value": {"type": ["string", "null"]},
                        "sensitivity_level": {"type": "string"},
                        "expected_action": {"type": "string"},
                    },
                },
            },
            "expected_policy_ops": {
                "type": "array",
                "items": {"type": "object"},
            },
            "expected_final_decision": {"type": "string"},
            "expected_missing_items": {
                "type": "array",
                "items": {"type": "string"},
            },
            "edge_case_tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "workflow_context": {
                "type": "object",
                "additionalProperties": True,
            },
        },
    }

