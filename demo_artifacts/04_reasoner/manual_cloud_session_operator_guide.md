# Manual Cloud Session Operator Guide

1. For the repository-internal baseline handoff, run `scripts/export_cloud_session_bundle.py --prepare-handoff`; for the manual Codex-session path, run `scripts/prepare_real_cloud_session.py --sample-id 0 --device auto`.
2. Open a second Codex session rooted at the generated handoff directory only: `cloud_session_handoff/` for the baseline package, or `real_cloud_session/handoff/` for the manual-session package.
3. In the second session, follow `OPEN_IN_SECOND_SESSION.md`, write `session_output/he_call_plan.json`, and run `python3 tools/run_real_he_eval.py --plan session_output/he_call_plan.json --output session_output/cloud_skill_output.json`.
4. Return to the main repository. For the baseline handoff, run `scripts/import_cloud_he_plan.py --plan cloud_session_handoff/session_output/cloud_skill_output.json` and then `scripts/run_he_ops_demo.py --sample-id 0`.
5. For the manual Codex-session path, run `scripts/import_real_cloud_he_plan.py --plan real_cloud_session/handoff/session_output/cloud_skill_output.json` and then `scripts/run_real_cloud_he_ops_demo.py --sample-id 0`.
6. Review the dedicated Streamlit pages and keep baseline artifacts separate from manual-session artifacts.
