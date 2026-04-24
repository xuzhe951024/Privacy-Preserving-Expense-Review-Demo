STATUS: FAIL

# Result Correctness Summary

- Dataset size: 1000
- Macro exact span F1: 0.9639
- Macro relaxed span F1: 0.9857
- Replacement correctness: 0.999
- Policy ops correctness: 1.0
- Final decision accuracy: 1.0
- Raw leakage count: 5
- Audit completeness: 1.0

## Entity Metrics

- AMOUNT: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- CARD_LAST4: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- COST_CENTER: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- DATE: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- EMAIL: exact F1=0.999, relaxed F1=0.999, false_positive_rate=0.001
- EMPLOYEE_ID: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- INVOICE_ID: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- PERSON: exact F1=0.715, relaxed F1=0.9547, false_positive_rate=0.316
- PHONE_NUMBER: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- PROJECT_CODE: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- VENDOR: exact F1=0.8886, relaxed F1=0.8886, false_positive_rate=0.2005

## Failure Samples

- exp_0657: expected=auto_approve, actual=auto_approve

## Current Boundaries

- The default detector uses rules plus native GLiNER when available; the heuristic detector is used only as a fallback.
- The default HE path uses Paillier additive homomorphic encryption for encrypted policy deltas.
- Ambiguous malformed values are routed to human review rather than guessed.
