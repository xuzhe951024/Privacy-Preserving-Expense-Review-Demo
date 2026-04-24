from __future__ import annotations

from src.demo_workflow import run_demo_flow


def test_final_decisions_match_expected_for_cap_and_missing_receipt(sample_client_dinner, sample_missing_receipt, tmp_path):
    over_result = run_demo_flow(sample_client_dinner, artifact_root=tmp_path / "over")
    receipt_result = run_demo_flow(sample_missing_receipt, artifact_root=tmp_path / "receipt")
    assert over_result["reassembly"]["final_decision_correctness"]["passed"] is True
    assert receipt_result["reassembly"]["final_decision_correctness"]["passed"] is True

