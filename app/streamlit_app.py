from __future__ import annotations

import json

import streamlit as st

from app.ui_helpers import read_text, render_json, render_text, run_script


def sidebar_actions(sample_id: str) -> None:
    st.sidebar.subheader("Run Actions")
    actions = [
        ("Run detection", ["scripts/run_eval.py", "--threshold", "0.3", "--device", "auto"]),
        ("Sanitize locally", ["scripts/export_cloud_session_bundle.py", "--sample-id", sample_id]),
        ("Export cloud session bundle", ["scripts/export_cloud_session_bundle.py", "--sample-id", sample_id]),
        ("Run cloud skill mock", ["scripts/run_cloud_reasoner_skill_mock.py", "--bundle", "cloud_session_bundle"]),
        ("Validate HE call plan", ["scripts/import_cloud_he_plan.py", "--plan", "demo_artifacts/04_reasoner/he_call_plan.json"]),
        ("Run Paillier HE ops", ["scripts/run_he_ops_demo.py", "--sample-id", sample_id]),
        ("Run local decryption and reassembly", ["scripts/run_e2e_demo.py", "--sample-id", sample_id]),
        ("Run leakage test", ["scripts/run_leakage_test.py", "--sample-id", sample_id]),
        ("Run correctness suite", ["scripts/run_correctness_suite.py", "--n", "64", "--seed", "42", "--threshold", "0.3", "--device", "auto"]),
    ]
    for label, command in actions:
        if st.sidebar.button(label, use_container_width=True):
            ok, output = run_script(*command)
            if ok:
                st.sidebar.success(output or "Completed.")
            else:
                st.sidebar.error(output or "Command failed.")


def build_download_bundle() -> bytes:
    manifest = {
        "audit_events": read_text("demo_artifacts/06_security/audit_events.jsonl"),
        "demo_script": read_text("demo_artifacts/08_showcase/demo_script.md"),
        "result_summary": read_text("demo_artifacts/09_validation/result_correctness_summary.md"),
    }
    return json.dumps(manifest, indent=2).encode("utf-8")


def main() -> None:
    st.set_page_config(page_title="Mock Cloud Session Demo", layout="wide")
    st.title("Mock Cloud Session Demo")
    st.caption("This page shows the repository-internal mock path only.")
    st.info(
        "Provenance: these outputs come from the built-in mock reasoner in this repository. "
        "Do not interpret them as results produced by a separately executed Codex session."
    )
    render_json("demo_artifacts/04_reasoner/mock_session_provenance.json")
    st.page_link("pages/1_Manual_Codex_Session_Simulation.py", label="Open Manual Codex Session Simulation Page")

    sample_id = st.sidebar.text_input("Sample ID or index", value="0")
    if st.sidebar.button("Run full demo", use_container_width=True):
        ok, output = run_script("scripts/run_e2e_demo.py", "--sample-id", sample_id)
        if ok:
            st.sidebar.success(output or "Completed.")
        else:
            st.sidebar.error(output or "Command failed.")
    if st.sidebar.button("Generate synthetic data", use_container_width=True):
        ok, output = run_script("scripts/gen_synthetic_data.py", "--n", "1000", "--seed", "42")
        if ok:
            st.sidebar.success(output or "Completed.")
        else:
            st.sidebar.error(output or "Command failed.")
    if st.sidebar.button("Run preflight env", use_container_width=True):
        ok, output = run_script("scripts/preflight_env.py")
        if ok:
            st.sidebar.success(output or "Completed.")
        else:
            st.sidebar.error(output or "Command failed.")

    sidebar_actions(sample_id)

    tabs = st.tabs(
        [
            "Raw Local Input",
            "Local Detection & Sanitization",
            "Cloud Bundle Preview",
            "Cloud Skill Output",
            "HE Ops Trace",
            "Local Decryption & Final Result",
            "Security & Correctness Dashboard",
        ]
    )

    with tabs[0]:
        st.subheader("Raw Local Input")
        render_text("demo_artifacts/01_data/dataset_preview.md")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Detection Samples")
            render_json("demo_artifacts/02_detection/detection_samples.json")
        with col2:
            st.markdown("#### Sanitized Payload")
            render_json("demo_artifacts/03_sanitization/sanitized_payload_examples.json")
            st.markdown("#### Leakage Check")
            render_json("demo_artifacts/03_sanitization/no_raw_leakage_check.json")

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Cloud Session Bundle")
            render_json("cloud_session_bundle/sanitized_request.json")
            st.markdown("#### Placeholder Metadata")
            render_json("cloud_session_bundle/placeholder_metadata.json")
        with col2:
            st.markdown("#### Public Policy Summary")
            render_json("cloud_session_bundle/policy_public_summary.json")
            st.markdown("#### Paillier Public HE Bundle")
            render_json("cloud_session_bundle/he_public_key.json")
            render_json("demo_artifacts/04_reasoner/real_he_encryption_report.json")
            st.markdown("#### No Raw Access Report")
            render_json("demo_artifacts/04_reasoner/cloud_session_no_raw_access_report.json")

    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Cloud Skill Output")
            render_json("demo_artifacts/04_reasoner/cloud_skill_output.json")
        with col2:
            st.markdown("#### HE Call Authorization")
            render_json("demo_artifacts/04_reasoner/he_call_authorization_report.json")
            st.markdown("#### Schema Validation")
            render_json("demo_artifacts/04_reasoner/he_call_plan_schema_validation.json")

    with tabs[4]:
        st.subheader("HE Ops Trace")
        st.markdown("#### Paillier HE Execution Report")
        render_json("demo_artifacts/05_reassembly/real_he_execution_report.json")
        st.markdown("#### Encrypted Result Handles")
        render_json("demo_artifacts/05_reassembly/he_ops_results_encrypted_handles.json")

    with tabs[5]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Local Decryption Report")
            render_json("demo_artifacts/05_reassembly/he_ops_local_decryption_report.json")
            st.markdown("#### Local Ops Results")
            render_json("demo_artifacts/05_reassembly/local_ops_results.json")
        with col2:
            st.markdown("#### Final User Visible Result")
            render_text("demo_artifacts/05_reassembly/final_user_visible_results.md")
            st.markdown("#### Final Decision Correctness")
            render_json("demo_artifacts/05_reassembly/final_decision_correctness_report.json")

    with tabs[6]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Leakage Report")
            render_json("demo_artifacts/06_security/leakage_report.json")
            st.markdown("#### Audit Events")
            st.code(read_text("demo_artifacts/06_security/audit_events.jsonl"), language="json")
        with col2:
            st.markdown("#### Correctness Summary")
            render_text("demo_artifacts/09_validation/result_correctness_summary.md")
            st.markdown("#### Demo Script")
            render_text("demo_artifacts/08_showcase/demo_script.md")

    st.download_button(
        "Download audit and showcase bundle",
        data=build_download_bundle(),
        file_name="privacy_expense_demo_showcase_bundle.json",
        mime="application/json",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
