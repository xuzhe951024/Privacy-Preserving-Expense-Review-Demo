from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_script(*args: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def read_json(path: str) -> dict | list | None:
    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return "Artifact not generated yet."
    return file_path.read_text(encoding="utf-8")


def render_json(path: str) -> None:
    payload = read_json(path)
    if payload is None:
        st.info("Artifact not generated yet.")
        return
    st.json(payload)


def render_text(path: str, language: str = "markdown") -> None:
    content = read_text(path)
    if language == "markdown":
        st.markdown(content)
    else:
        st.code(content, language=language)


def sidebar_actions(sample_id: str) -> None:
    st.sidebar.subheader("Run Actions")
    actions = [
        ("Run detection", ["scripts/run_eval.py", "--threshold", "0.3", "--device", "auto"]),
        ("Sanitize locally", ["scripts/export_cloud_session_bundle.py", "--sample-id", sample_id]),
        ("Export cloud session bundle", ["scripts/export_cloud_session_bundle.py", "--sample-id", sample_id]),
        ("Run cloud skill mock", ["scripts/run_cloud_reasoner_skill_mock.py", "--bundle", "cloud_session_bundle"]),
        ("Validate HE call plan", ["scripts/import_cloud_he_plan.py", "--plan", "demo_artifacts/04_reasoner/he_call_plan.json"]),
        ("Run HE ops mock", ["scripts/run_he_ops_demo.py", "--sample-id", sample_id]),
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
    st.set_page_config(page_title="Privacy-Preserving Expense Review Demo", layout="wide")
    st.title("Privacy-Preserving Expense Review Demo")
    st.caption("Local session, isolated cloud bundle, HE-style tool calls, and local-only reassembly.")

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

