# Second Session Instructions

Open a new Codex session rooted in this directory only.

Your task is to act as the isolated cloud-side reasoner for a privacy-preserving expense review demo.

## Files You May Read

- `cloud_session_bundle/sanitized_request.json`
- `cloud_session_bundle/placeholder_metadata.json`
- `cloud_session_bundle/policy_public_summary.json`
- `cloud_session_bundle/he_public_key.json`
- `cloud_session_bundle/he_ciphertexts.json`
- `cloud_session_bundle/he_policy_operands.json`
- `skills/privacy_expense_cloud_reasoner/SKILL.md`
- `skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json`
- `skills/privacy_expense_cloud_reasoner/schemas/cloud_reasoner_response.schema.json`
- `tools/run_real_he_eval.py`

## Hard Restrictions

- Do not ask for raw values.
- Do not ask for decrypt, reveal, lookup_vault, print_raw, or any plaintext recovery action.
- Do not invent numeric values behind placeholders.
- Do not read or reference files outside this directory.
- Do not fabricate HE results. You must run `tools/run_real_he_eval.py` to produce encrypted results.

## Required Output

First write an HE call plan to `session_output/he_call_plan.json`.

Then run:

```bash
python3 tools/run_real_he_eval.py --plan session_output/he_call_plan.json --output session_output/cloud_skill_output.json
```

The final JSON file must be `session_output/cloud_skill_output.json`.

- The JSON must match `skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json`.
- The JSON must include `he_evaluation` produced by the Paillier HE evaluator tool.
- Use only placeholder handles and public policy keys.
- If metadata is insufficient, return `needs_human_review` with an empty `requested_he_ops` array.
