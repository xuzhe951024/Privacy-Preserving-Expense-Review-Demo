from __future__ import annotations

from src.demo_workflow import run_demo_flow
from src.synthetic_data import build_named_edge_case


def test_edge_cases_route_safely(tmp_path):
    malformed = build_named_edge_case("malformed_amount", sample_index=10)
    missing_policy = build_named_edge_case("missing_policy_cap", sample_index=11)
    malformed_result = run_demo_flow(malformed, artifact_root=tmp_path / "malformed")
    missing_policy_result = run_demo_flow(missing_policy, artifact_root=tmp_path / "missing_policy")
    assert malformed_result["reassembly"]["actual_final_decision"] == "needs_human_review"
    assert missing_policy_result["reassembly"]["actual_final_decision"] == "needs_human_review"

