from __future__ import annotations

from copy import deepcopy


ENTITY_POLICY = {
    "PERSON": {"action": "tokenize_encrypt"},
    "EMAIL": {"action": "tokenize_encrypt"},
    "PHONE_NUMBER": {"action": "tokenize_encrypt"},
    "EMPLOYEE_ID": {"action": "tokenize_encrypt"},
    "CARD_LAST4": {"action": "tokenize_encrypt"},
    "AMOUNT": {
        "action": "tokenize_encrypt",
        "allowed_ops": ["compare_policy_cap", "sum", "subtract"],
        "allowed_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap", "fhe_sum_amounts", "fhe_min_policy_cap"],
    },
    "DATE": {
        "action": "tokenize_encrypt",
        "allowed_ops": ["compare_submission_window"],
        "allowed_he_ops": ["fhe_compare_date_window"],
    },
    "INVOICE_ID": {"action": "tokenize_encrypt"},
    "PROJECT_CODE": {"action": "tokenize_encrypt"},
    "COST_CENTER": {"action": "tokenize_encrypt"},
    "VENDOR": {"action": "tokenize_or_category"},
}

ALLOWED_HE_OPS = {
    "fhe_compare_policy_cap",
    "fhe_subtract_policy_cap",
    "fhe_sum_amounts",
    "fhe_compare_date_window",
    "fhe_min_policy_cap",
}

HE_OP_TO_LOCAL_OP = {
    "fhe_compare_policy_cap": "compare_policy_cap",
    "fhe_subtract_policy_cap": "subtract",
    "fhe_sum_amounts": "sum",
    "fhe_compare_date_window": "compare_submission_window",
    "fhe_min_policy_cap": "compare_policy_cap",
}

POLICY_VALUES = {
    "meal_cap_usd": 45_000,
    "hotel_cap_usd": 65_000,
    "airfare_cap_usd": 125_000,
    "taxi_cap_usd": 12_000,
    "software_subscription_cap_usd": 120_000,
    "submission_window_days": 30,
}

PUBLIC_POLICY_SUMMARY = {
    "meal_cap_usd": {
        "scope": "local_only",
        "description": "Meal expenses require local cap validation.",
        "supported_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap", "fhe_min_policy_cap"],
    },
    "hotel_cap_usd": {
        "scope": "local_only",
        "description": "Hotel expenses require local cap validation.",
        "supported_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap"],
    },
    "airfare_cap_usd": {
        "scope": "local_only",
        "description": "Airfare expenses require local cap validation.",
        "supported_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap"],
    },
    "taxi_cap_usd": {
        "scope": "local_only",
        "description": "Taxi and rideshare expenses require local cap validation.",
        "supported_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap"],
    },
    "software_subscription_cap_usd": {
        "scope": "local_only",
        "description": "Software subscriptions require local cap validation.",
        "supported_he_ops": ["fhe_compare_policy_cap", "fhe_subtract_policy_cap"],
    },
    "submission_window_days": {
        "scope": "local_only",
        "description": "Expense submission timing must be verified locally.",
        "supported_he_ops": ["fhe_compare_date_window"],
    },
}


def get_entity_policy(label: str) -> dict[str, object]:
    return deepcopy(ENTITY_POLICY.get(label, {"action": "tokenize_encrypt"}))


def get_public_policy_summary() -> dict[str, object]:
    return deepcopy(PUBLIC_POLICY_SUMMARY)


def get_policy_value(policy_key: str) -> int | None:
    return POLICY_VALUES.get(policy_key)


def token_label(label: str) -> str:
    return label.upper()

