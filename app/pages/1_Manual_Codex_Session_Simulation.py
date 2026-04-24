from __future__ import annotations

import streamlit as st

from app.ui_helpers import read_text, render_json, render_text, run_script


def sidebar_actions(sample_id: str) -> None:
    st.sidebar.subheader("Manual Session Actions")
    actions = [
        (
            "Prepare Real Session",
            ["scripts/prepare_real_cloud_session.py", "--sample-id", sample_id, "--device", "auto"],
        ),
        (
            "Import Returned Plan",
            ["scripts/import_real_cloud_he_plan.py"],
        ),
        (
            "Run Paillier HE Reassembly",
            ["scripts/run_real_cloud_he_ops_demo.py", "--sample-id", sample_id],
        ),
    ]
    for label, command in actions:
        if st.sidebar.button(label, use_container_width=True):
            ok, output = run_script(*command)
            if ok:
                st.sidebar.success(output or "Completed.")
            else:
                st.sidebar.error(output or "Command failed.")


def main() -> None:
    st.set_page_config(page_title="Manual Codex Session Simulation", layout="wide")
    st.title("Manual Codex Session Simulation")
    st.caption("This page shows outputs produced by a separately operated second Codex session over the sanitized handoff package.")
    st.warning(
        "Interpretation: this is not the repository-internal mock path, but it is still a demo simulation of the cloud reasoning role rather than a production cloud service."
    )
    render_json("demo_artifacts/10_real_cloud_session/manual_codex_session_provenance.json")
    st.page_link("streamlit_app.py", label="Open Mock Cloud Session Page")

    sample_id = st.sidebar.text_input("Sample ID or index", value="0")
    sidebar_actions(sample_id)

    st.markdown("### Provenance And Separation Summary")
    render_json("demo_artifacts/10_real_cloud_session/real_session_isolation_report.json")

    tabs = st.tabs(
        [
            "Preparation",
            "Second Session Package",
            "Imported Manual-Session Plan",
            "Manual-Session Reassembly",
            "Security",
            "Operator Guide",
        ]
    )

    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Manual Session Index")
            render_json("demo_artifacts/10_real_cloud_session/real_cloud_session_index.json")
        with col2:
            st.markdown("#### Manual Session Sanitization Output")
            render_json("demo_artifacts/10_real_cloud_session/03_sanitization/sanitized_payload_examples.json")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Handoff Files")
            st.code(
                read_text("real_cloud_session/handoff/OPEN_IN_SECOND_SESSION.md"),
                language="markdown",
            )
        with col2:
            st.markdown("#### Handoff Manifest")
            render_json("real_cloud_session/handoff/handoff_manifest.json")
            st.markdown("#### Returned Plan Location")
            st.code("real_cloud_session/handoff/session_output/cloud_skill_output.json", language="text")

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Imported Manual-Session Output")
            render_json("demo_artifacts/10_real_cloud_session/04_reasoner/cloud_skill_output.json")
        with col2:
            st.markdown("#### Schema Validation")
            render_json("demo_artifacts/10_real_cloud_session/04_reasoner/he_call_plan_schema_validation.json")
            st.markdown("#### Authorization Report")
            render_json("demo_artifacts/10_real_cloud_session/04_reasoner/he_call_authorization_report.json")
            st.markdown("#### Paillier HE Evaluation")
            render_json("demo_artifacts/10_real_cloud_session/04_reasoner/manual_session_he_evaluation.json")

    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### HE Results")
            render_json("demo_artifacts/10_real_cloud_session/05_reassembly/he_ops_results_encrypted_handles.json")
            st.markdown("#### Local Decryption Report")
            render_json("demo_artifacts/10_real_cloud_session/05_reassembly/he_ops_local_decryption_report.json")
        with col2:
            st.markdown("#### Final User Visible Result")
            render_text("demo_artifacts/10_real_cloud_session/05_reassembly/final_user_visible_results.md")
            st.markdown("#### Final Decision Correctness")
            render_json("demo_artifacts/10_real_cloud_session/05_reassembly/final_decision_correctness_report.json")

    with tabs[4]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Manual-Session No-Raw-Leakage Report")
            render_json("demo_artifacts/10_real_cloud_session/06_security/cloud_skill_output_no_raw_leakage_report.json")
        with col2:
            st.markdown("#### Manual-Session Audit Events")
            st.code(read_text("demo_artifacts/10_real_cloud_session/06_security/audit_events_real.jsonl"), language="json")

    with tabs[5]:
        st.markdown("#### Manual Session Operator Guide")
        render_text("demo_artifacts/10_real_cloud_session/manual_real_cloud_session_operator_guide.md")
        st.markdown("#### Manual Session Demo Script")
        render_text("demo_artifacts/10_real_cloud_session/08_showcase/real_cloud_session_demo_script.md")


if __name__ == "__main__":
    main()
