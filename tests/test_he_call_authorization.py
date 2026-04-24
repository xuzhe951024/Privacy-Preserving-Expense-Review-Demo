from __future__ import annotations

from src.cloud_reasoner_mock import validate_authorized_he_ops


def test_unauthorized_he_ops_are_rejected():
    metadata = {"AMOUNT_1": {"entity_type": "AMOUNT", "allowed_he_ops": ["fhe_subtract_policy_cap"]}}
    invalid_plan = {
        "requested_he_ops": [
            {
                "op_id": "op_001",
                "op": "decrypt",
                "ciphertext_handle": "AMOUNT_1",
                "return_as": "plaintext",
            }
        ]
    }
    report = validate_authorized_he_ops(invalid_plan, metadata)
    assert report["authorized"] is False
