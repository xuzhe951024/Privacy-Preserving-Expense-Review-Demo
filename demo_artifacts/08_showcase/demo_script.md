# Demo Script

## Phase-by-phase showcase

- Phase 0: Show `demo_artifacts/00_env/env_report.md` to prove isolated environment usage, GPU-first runtime selection, and CPU fallback.
- Phase 1: Show `demo_artifacts/01_data/dataset_preview.md` to explain that the dataset is fully synthetic.
- Phase 2: Show `demo_artifacts/02_detection/detection_metrics_by_entity.csv` and `threshold_sweep.csv` to explain detector coverage and precision/recall tradeoffs.
- Phase 3: Show `demo_artifacts/03_sanitization/sanitized_payload_examples.json` and `no_raw_leakage_check.json` to prove sanitized-only cloud requests.
- Phase 4: Show `cloud_session_bundle/`, `real_cloud_session/handoff/`, and `demo_artifacts/04_reasoner/he_call_plan.json` to explain the cloud boundary, manual second-session package, and restricted Paillier HE planning.
- Phase 5: Show `demo_artifacts/05_reassembly/he_ops_local_decryption_report.json` and `final_user_visible_results.md` to explain that only the local side sees decrypted outcomes.
- Phase 6: Show `demo_artifacts/06_security/leakage_report.json` and `audit_events.jsonl` to prove leakage testing and audit completeness.
- Phase 7: Walk through the Streamlit tabs to contrast local raw input, cloud bundle preview, HE trace, and final local result.

## 90-second narration

1. On the left is the raw local expense text with names, employee IDs, amounts, card last four, and email addresses.
2. The local detector identifies strong-format fields with rules and runs native GLiNER when available for names and vendors.
3. The system stores raw values in the local vault, replaces them with placeholders, and proves the outbound payload has zero raw leakage.
4. The Cloud Bundle panel shows what an isolated cloud session actually receives: sanitized text, placeholder metadata, and public policy summaries only.
5. For the manual-session demo, open a second Codex session on `real_cloud_session/handoff/` only. That session can read the sanitized bundle, the cloud skill, public Paillier material, and the evaluator tool, but not the local vault, private key, or raw source text.
6. The cloud skill can only return an allowlisted Paillier HE call plan such as summing encrypted amount handles and subtracting an encrypted policy cap.
7. The HE trace shows that the cloud sees encrypted input handles and encrypted result handles, not plaintext amounts.
8. Only the local side decrypts the result handles and combines them with local policy logic to produce the final routing decision.
9. The dashboard shows no raw leakage, no unauthorized cloud ops, and final decision correctness against a synthetic oracle.
