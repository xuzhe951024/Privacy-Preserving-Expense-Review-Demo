from __future__ import annotations

from src.detector_rules import detect_rule_entities


def test_rule_detector_finds_strong_format_fields(sample_client_dinner):
    labels = {entity.label for entity in detect_rule_entities(sample_client_dinner.raw_text)}
    expected = {
        "EMAIL",
        "PHONE_NUMBER",
        "EMPLOYEE_ID",
        "INVOICE_ID",
        "PROJECT_CODE",
        "COST_CENTER",
        "CARD_LAST4",
        "AMOUNT",
        "DATE",
    }
    assert expected <= labels

