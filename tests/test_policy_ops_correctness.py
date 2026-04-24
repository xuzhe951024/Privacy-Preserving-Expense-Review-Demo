from __future__ import annotations

import random

from src.demo_workflow import run_demo_flow
from src.synthetic_data import build_client_dinner


def test_policy_ops_cover_over_under_and_boundary_cases(tmp_path):
    over = build_client_dinner(0, random.Random(42), amount=482.15)
    within = build_client_dinner(1, random.Random(43), amount=430.00)
    boundary = build_client_dinner(2, random.Random(44), amount=450.00)

    over_result = run_demo_flow(over, artifact_root=tmp_path / "over")
    within_result = run_demo_flow(within, artifact_root=tmp_path / "within")
    boundary_result = run_demo_flow(boundary, artifact_root=tmp_path / "boundary")

    assert over_result["reassembly"]["policy_ops_correctness"]["passed"] is True
    assert over_result["reassembly"]["actual_final_decision"] == "needs_manager_approval"
    assert within_result["reassembly"]["actual_final_decision"] == "auto_approve"
    assert boundary_result["reassembly"]["actual_final_decision"] == "auto_approve"

