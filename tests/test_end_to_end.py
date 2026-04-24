from __future__ import annotations

from src.demo_workflow import run_demo_flow


def test_end_to_end_generates_expected_artifacts(sample_client_dinner, tmp_path):
    result = run_demo_flow(sample_client_dinner, artifact_root=tmp_path)
    assert result["reassembly"]["final_decision_correctness"]["passed"] is True
    assert (tmp_path / "demo_artifacts" / "03_sanitization" / "sanitized_payload_examples.json").exists()
    assert (tmp_path / "demo_artifacts" / "04_reasoner" / "he_call_plan.json").exists()
    assert (tmp_path / "demo_artifacts" / "05_reassembly" / "end_to_end_trace.json").exists()

