# Minimal Context Comparison

## Standard sanitized payload

```json
{
  "sanitized_text": "Employee <PERSON_1> submitted a team offsite meal summary: meal <AMOUNT_1>, tip <AMOUNT_2>, tax <AMOUNT_3> on <DATE_1> at <VENDOR_1>. Invoice <INVOICE_ID_1>, project <PROJECT_CODE_1>, cost center <COST_CENTER_1>, employee ID <EMPLOYEE_ID_1>, email <EMAIL_1>, phone <PHONE_NUMBER_1>.",
  "public_context": {
    "workflow_type": "expense_review",
    "expense_type": "team_offsite",
    "currency": "USD",
    "policy_key": "meal_cap_usd",
    "receipt_attached": true,
    "requires_sum": true,
    "requires_cap_validation": true,
    "amount_handles_expected": 3
  },
  "metadata_keys": [
    "PERSON_1",
    "AMOUNT_1",
    "AMOUNT_2",
    "AMOUNT_3",
    "DATE_1",
    "VENDOR_1",
    "INVOICE_ID_1",
    "PROJECT_CODE_1",
    "COST_CENTER_1",
    "EMPLOYEE_ID_1",
    "EMAIL_1",
    "PHONE_NUMBER_1"
  ]
}
```

## Minimal payload

```json
{
  "sample_id": "exp_0001",
  "sanitized_text": "Employee <PERSON_1> submitted a team offsite meal summary: meal <AMOUNT_1>, tip <AMOUNT_2>, tax <AMOUNT_3> on <DATE_1> at <VENDOR_1>. Invoice <INVOICE_ID_1>, project <PROJECT_CODE_1>, cost center <COST_CENTER_1>, employee ID <EMPLOYEE_ID_1>, email <EMAIL_1>, phone <PHONE_NUMBER_1>.",
  "public_context": {
    "expense_type": "team_offsite",
    "policy_key": "meal_cap_usd",
    "receipt_attached": true
  },
  "metadata": {
    "PERSON_1": {
      "entity_type": "PERSON"
    },
    "AMOUNT_1": {
      "entity_type": "AMOUNT"
    },
    "AMOUNT_2": {
      "entity_type": "AMOUNT"
    },
    "AMOUNT_3": {
      "entity_type": "AMOUNT"
    },
    "DATE_1": {
      "entity_type": "DATE"
    },
    "VENDOR_1": {
      "entity_type": "VENDOR"
    },
    "INVOICE_ID_1": {
      "entity_type": "INVOICE_ID"
    },
    "PROJECT_CODE_1": {
      "entity_type": "PROJECT_CODE"
    },
    "COST_CENTER_1": {
      "entity_type": "COST_CENTER"
    },
    "EMPLOYEE_ID_1": {
      "entity_type": "EMPLOYEE_ID"
    },
    "EMAIL_1": {
      "entity_type": "EMAIL"
    },
    "PHONE_NUMBER_1": {
      "entity_type": "PHONE_NUMBER"
    }
  }
}
```

The minimal payload removes scores, sources, and detailed allowed-op metadata. This reduces context but can increase the chance of human review because the cloud reasoner has less routing context.
