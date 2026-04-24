STATUS: PASS

# Result Correctness Summary

- Dataset size: 1000
- Macro exact span F1: 0.9839
- Macro relaxed span F1: 0.9946
- Replacement correctness: 1.0
- Policy ops correctness: 1.0
- Final decision accuracy: 1.0
- Raw leakage count: 0
- Audit completeness: 1.0

## Entity Metrics

- AMOUNT: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- CARD_LAST4: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- COST_CENTER: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- DATE: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- EMAIL: exact F1=0.999, relaxed F1=0.999, false_positive_rate=0.001
- EMPLOYEE_ID: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- INVOICE_ID: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- PERSON: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- PHONE_NUMBER: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- PROJECT_CODE: exact F1=1.0, relaxed F1=1.0, false_positive_rate=0.0
- VENDOR: exact F1=0.8234, relaxed F1=0.9415, false_positive_rate=0.2221

## Failure Samples

- None

## Current Boundaries

- The default detector uses rules plus a GLiNER-compatible fallback heuristic unless the GLiNER model is available.
- Real TFHE-rs execution is intentionally out of scope for the default path.
- Ambiguous malformed values are routed to human review rather than guessed.
