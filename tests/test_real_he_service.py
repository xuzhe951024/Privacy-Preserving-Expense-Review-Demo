from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.cloud_bundle_exporter import export_cloud_bundle
from src.cloud_reasoner_mock import build_cloud_skill_response
from src.demo_workflow import detect_sample
from src.he_service import evaluate_he_plan_public, execute_he_plan
from src.reassembler import reassemble_results
from src.sanitizer import sanitize_sample
from src.audit import AuditLogger
from src.vault import Vault


def test_paillier_he_evaluates_policy_delta_without_plaintext(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    export_cloud_bundle(
        payload,
        sample_client_dinner,
        bundle_dir=tmp_path / "bundle",
        artifact_dir=tmp_path / "reasoner",
        vault=vault,
        he_key_path=tmp_path / "paillier.key.json",
    )
    plan = build_cloud_skill_response(
        {
            "sample_id": payload.sample_id,
            "session_id": payload.session_id,
            "sanitized_text": payload.sanitized_text,
            "metadata": payload.metadata,
            "policy_summary": payload.policy_summary,
            "public_context": payload.public_context,
        }
    )

    assert all(operation["op"] != "fhe_compare_policy_cap" for operation in plan["requested_he_ops"])
    evaluation = evaluate_he_plan_public(plan, bundle_dir=tmp_path / "bundle")
    assert evaluation["scheme"] == "paillier"
    assert evaluation["he_results"]
    assert all("ciphertext" in result for result in evaluation["he_results"])

    he_results = execute_he_plan(
        {**plan, "he_evaluation": evaluation},
        payload.session_id,
        artifact_dir=tmp_path / "reassembly",
        result_store_dir=tmp_path / "he_results",
        bundle_dir=tmp_path / "bundle",
        key_path=tmp_path / "paillier.key.json",
    )
    reassembly = reassemble_results(
        sample_client_dinner,
        payload,
        plan,
        he_results,
        AuditLogger(),
        artifact_dir=tmp_path / "reassembly",
        result_store_dir=tmp_path / "he_results",
    )
    assert reassembly["policy_ops_correctness"]["passed"] is True
    assert reassembly["final_decision_correctness"]["passed"] is True


def test_handoff_he_tool_writes_enriched_output(sample_client_dinner, tmp_path):
    detection = detect_sample(sample_client_dinner)
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    payload = sanitize_sample(sample_client_dinner, detection["resolved_entities"], vault, artifact_dir=tmp_path / "artifacts")
    export_cloud_bundle(
        payload,
        sample_client_dinner,
        bundle_dir=tmp_path / "handoff" / "cloud_session_bundle",
        artifact_dir=tmp_path / "reasoner",
        vault=vault,
        he_key_path=tmp_path / "paillier.key.json",
    )
    from src.cloud_session_handoff import REAL_HE_EVALUATOR_TOOL

    tool_path = tmp_path / "handoff" / "tools" / "run_real_he_eval.py"
    tool_path.parent.mkdir(parents=True, exist_ok=True)
    tool_path.write_text(REAL_HE_EVALUATOR_TOOL, encoding="utf-8")
    plan = build_cloud_skill_response(
        {
            "sample_id": payload.sample_id,
            "session_id": payload.session_id,
            "sanitized_text": payload.sanitized_text,
            "metadata": payload.metadata,
            "policy_summary": payload.policy_summary,
            "public_context": payload.public_context,
        }
    )
    plan_path = tmp_path / "handoff" / "session_output" / "he_call_plan.json"
    output_path = tmp_path / "handoff" / "session_output" / "cloud_skill_output.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(tool_path),
            "--bundle",
            str(tmp_path / "handoff" / "cloud_session_bundle"),
            "--plan",
            str(plan_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["he_execution_required"] == "paillier_public_evaluator"
    assert output["he_evaluation"]["scheme"] == "paillier"
    assert output["he_evaluation"]["he_results"]
