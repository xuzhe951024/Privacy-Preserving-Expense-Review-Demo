from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.audit import AuditLogger
from src.cloud_bundle_exporter import export_cloud_bundle
from src.cloud_reasoner_client import validate_against_schema
from src.cloud_reasoner_mock import validate_authorized_he_ops
from src.cloud_session_handoff import prepare_isolated_cloud_session_handoff
from src.demo_workflow import detect_sample
from src.he_service import execute_he_plan, extract_plan_and_evaluation
from src.leakage_scan import safe_json_text_for_leakage_scan
from src.models import ExpenseSample, SanitizedPayload
from src.pipeline import load_samples_from_truth, select_sample
from src.reassembler import reassemble_results
from src.report_writer import write_json, write_markdown
from src.sanitizer import sanitize_sample
from src.synthetic_data import generate_samples, save_dataset
from src.vault import Vault


@dataclass(slots=True)
class RealCloudSessionPaths:
    root_dir: str = "real_cloud_session"
    artifact_root: str = "demo_artifacts/10_real_cloud_session"
    result_store_dir: str = ".local/he_results_real"
    vault_key_path: str = ".secrets/real_cloud_session/vault.key"
    vault_db_path: str = ".local/real_cloud_session/vault.sqlite"
    he_key_path: str = ".secrets/real_cloud_session/paillier_demo_key.json"

    @property
    def root(self) -> Path:
        return Path(self.root_dir)

    @property
    def bundle_dir(self) -> Path:
        return self.root / "bundle"

    @property
    def handoff_dir(self) -> Path:
        return self.root / "handoff"

    @property
    def returned_plan_path(self) -> Path:
        return self.handoff_dir / "session_output" / "cloud_skill_output.json"

    @property
    def sanitization_dir(self) -> Path:
        return Path(self.artifact_root) / "03_sanitization"

    @property
    def reasoner_dir(self) -> Path:
        return Path(self.artifact_root) / "04_reasoner"

    @property
    def reassembly_dir(self) -> Path:
        return Path(self.artifact_root) / "05_reassembly"

    @property
    def security_dir(self) -> Path:
        return Path(self.artifact_root) / "06_security"

    @property
    def showcase_dir(self) -> Path:
        return Path(self.artifact_root) / "08_showcase"

    @property
    def vault_key(self) -> Path:
        return Path(self.vault_key_path)

    @property
    def vault_db(self) -> Path:
        return Path(self.vault_db_path)

    @property
    def he_key(self) -> Path:
        return Path(self.he_key_path)

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data.update(
            {
                "bundle_dir": str(self.bundle_dir),
                "handoff_dir": str(self.handoff_dir),
                "returned_plan_path": str(self.returned_plan_path),
                "sanitization_dir": str(self.sanitization_dir),
                "reasoner_dir": str(self.reasoner_dir),
                "reassembly_dir": str(self.reassembly_dir),
                "security_dir": str(self.security_dir),
                "showcase_dir": str(self.showcase_dir),
                "vault_key_path": str(self.vault_key),
                "vault_db_path": str(self.vault_db),
                "he_key_path": str(self.he_key),
            }
        )
        return data


def _build_real_vault(paths: RealCloudSessionPaths) -> Vault:
    return Vault(paths.vault_key, paths.vault_db)


def ensure_samples() -> list[ExpenseSample]:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def _load_sanitized_payload(path: str | Path) -> SanitizedPayload:
    payload_dict = json.loads(Path(path).read_text(encoding="utf-8"))
    return SanitizedPayload(
        sample_id=payload_dict["sample_id"],
        session_id=payload_dict["session_id"],
        sanitized_text=payload_dict["sanitized_text"],
        metadata=payload_dict["metadata"],
        policy_summary=payload_dict["policy_summary"],
        public_context=payload_dict["public_context"],
        replacement_report=payload_dict.get("replacement_report", {}),
        leakage_check=payload_dict.get("leakage_check", {}),
        token_preview=payload_dict.get("token_preview", []),
    )


def _candidate_strings(entity: dict[str, Any]) -> list[str]:
    values = [entity["text"]]
    normalized = entity.get("normalized_value")
    if normalized:
        values.append(normalized)
        if entity["label"] == "AMOUNT":
            values.append(str(normalized).replace(".", ""))
    return [value for value in values if value]


def _write_real_session_index(paths: RealCloudSessionPaths, sample: ExpenseSample) -> None:
    write_json(
        Path(paths.artifact_root) / "real_cloud_session_index.json",
        {
            "sample_id": sample.sample_id,
            "paths": paths.to_dict(),
            "mock_isolation_statement": {
                "mock_bundle_dir": "cloud_session_bundle",
                "mock_handoff_dir": "cloud_session_handoff",
                "mock_reasoner_dir": "demo_artifacts/04_reasoner",
                "mock_reassembly_dir": "demo_artifacts/05_reassembly",
                "real_bundle_dir": str(paths.bundle_dir),
                "real_handoff_dir": str(paths.handoff_dir),
                "real_reasoner_dir": str(paths.reasoner_dir),
                "real_reassembly_dir": str(paths.reassembly_dir),
            },
        },
    )


def _write_real_session_showcase(paths: RealCloudSessionPaths) -> None:
    write_markdown(
        paths.showcase_dir / "real_cloud_session_demo_script.md",
        "\n".join(
            [
                "# Manual Codex Session Simulation Demo Script",
                "",
                "1. Show that the mock path and the manual second-session path write to different directories.",
                "2. Export the sanitized handoff package and open `real_cloud_session/handoff/` in a second Codex session.",
                "3. Have the second session produce `session_output/he_call_plan.json`, run `tools/run_real_he_eval.py`, and produce `session_output/cloud_skill_output.json` without access to the main repository, local vault, or secrets.",
                "4. Import the returned plan into `demo_artifacts/10_real_cloud_session/04_reasoner/` only.",
                "5. Run Paillier HE result decryption and local reassembly into `demo_artifacts/10_real_cloud_session/05_reassembly/` only.",
                "6. Open the dedicated Streamlit manual-session page and verify that it does not display mock artifacts.",
                "7. Explain that this path is still a simulation of the cloud reasoning role, but its output was produced by a separately operated Codex session instead of the repository-internal mock.",
            ]
        ),
    )


def _manual_session_provenance(plan_imported: bool, paths: RealCloudSessionPaths) -> dict[str, Any]:
    return {
        "session_label": "manual_codex_session_simulation",
        "execution_mode": "separate_manual_codex_session",
        "producer": "user-operated second Codex session over real_cloud_session/handoff/",
        "separate_codex_session": True,
        "plan_imported": plan_imported,
        "returned_plan_path": str(paths.returned_plan_path),
        "interpretation_note": (
            "This path represents a manually operated second Codex session that simulates the cloud reasoning role. "
            "It is distinct from the repository-internal mock path, but it is still a demo simulation rather than a production cloud deployment."
        ),
    }


def prepare_real_cloud_session(
    sample_id: str = "0",
    threshold: float = 0.3,
    device: str = "auto",
    paths: RealCloudSessionPaths | None = None,
) -> dict[str, Any]:
    session_paths = paths or RealCloudSessionPaths()
    samples = ensure_samples()
    sample = select_sample(samples, sample_id)
    detection = detect_sample(sample, threshold=threshold, device=device)
    vault = _build_real_vault(session_paths)
    sanitized_payload = sanitize_sample(sample, detection["resolved_entities"], vault, artifact_dir=session_paths.sanitization_dir)
    bundle_export = export_cloud_bundle(
        sanitized_payload,
        sample,
        bundle_dir=session_paths.bundle_dir,
        artifact_dir=session_paths.reasoner_dir,
        vault=vault,
        he_key_path=session_paths.he_key,
    )
    handoff = prepare_isolated_cloud_session_handoff(
        bundle_dir=session_paths.bundle_dir,
        handoff_dir=session_paths.handoff_dir,
        artifact_dir=session_paths.reasoner_dir,
    )
    _write_real_session_index(session_paths, sample)
    _write_real_session_showcase(session_paths)
    write_json(
        Path(session_paths.artifact_root) / "manual_codex_session_provenance.json",
        _manual_session_provenance(plan_imported=False, paths=session_paths),
    )
    write_json(
        Path(session_paths.artifact_root) / "real_session_isolation_report.json",
        {
            "passed": True,
            "real_paths": session_paths.to_dict(),
            "mock_paths": {
                "bundle_dir": "cloud_session_bundle",
                "handoff_dir": "cloud_session_handoff",
                "reasoner_dir": "demo_artifacts/04_reasoner",
                "reassembly_dir": "demo_artifacts/05_reassembly",
                "vault_key_path": ".secrets/vault.key",
                "vault_db_path": ".local/vault.sqlite",
                "he_key_path": ".secrets/paillier_demo_key.json",
            },
            "rules": [
                "Real cloud-session outputs are written under real_cloud_session/ and demo_artifacts/10_real_cloud_session/ only.",
                "Mock artifacts remain under cloud_session_bundle/, cloud_session_handoff/, demo_artifacts/04_reasoner/, and demo_artifacts/05_reassembly/.",
                "Returned plans from the real session must be imported into demo_artifacts/10_real_cloud_session/04_reasoner/ only.",
                "Real cloud-session vault material is written under .secrets/real_cloud_session/ and .local/real_cloud_session/ only.",
                "Manual second-session HE evaluation uses Paillier public-key ciphertexts and does not require local plaintext or private keys.",
                "The real-session runtime directories are git-ignored so that real outputs are not mixed into tracked mock artifacts.",
                "The purpose of the separate path is also provenance clarity: manual second-session outputs must never be mistaken for repository-internal mock outputs.",
            ],
        },
    )
    write_markdown(
        Path(session_paths.artifact_root) / "manual_real_cloud_session_operator_guide.md",
        "\n".join(
            [
                "# Manual Codex Session Simulation Operator Guide",
                "",
                "1. Run `scripts/prepare_real_cloud_session.py --sample-id 0 --device auto` in the main repository.",
                "2. Open a second Codex session rooted at `real_cloud_session/handoff/` only.",
                "3. In the second session, follow `OPEN_IN_SECOND_SESSION.md`, write `session_output/he_call_plan.json`, and run the bundled Paillier HE evaluator to produce `session_output/cloud_skill_output.json`.",
                "4. Return to the main repository and run `scripts/import_real_cloud_he_plan.py`.",
                "5. Run `scripts/run_real_cloud_he_ops_demo.py --sample-id 0`.",
                "6. Review isolated local state under `.secrets/real_cloud_session/` and `.local/real_cloud_session/` if needed.",
                "7. Open the Streamlit page `Manual Codex Session Simulation` to review the isolated results.",
                "8. When presenting results, explicitly distinguish this page from the `Mock Cloud Session Demo` page.",
            ]
        ),
    )
    return {
        "sample": sample,
        "bundle_export": bundle_export,
        "handoff": handoff,
        "paths": session_paths,
    }


def import_real_cloud_plan(
    plan_path: str | Path | None = None,
    paths: RealCloudSessionPaths | None = None,
) -> dict[str, Any]:
    session_paths = paths or RealCloudSessionPaths()
    resolved_plan_path = Path(plan_path) if plan_path else session_paths.returned_plan_path
    output_payload = json.loads(resolved_plan_path.read_text(encoding="utf-8"))
    plan, he_evaluation = extract_plan_and_evaluation(output_payload)
    bundle_request = json.loads((session_paths.bundle_dir / "sanitized_request.json").read_text(encoding="utf-8"))
    metadata = json.loads((session_paths.bundle_dir / "placeholder_metadata.json").read_text(encoding="utf-8"))
    schema_validation = validate_against_schema(plan, "skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json")
    authorization_report = validate_authorized_he_ops(plan, metadata)

    samples = ensure_samples()
    sample = select_sample(samples, bundle_request["sample_id"])
    plan_blob = safe_json_text_for_leakage_scan({"plan": plan, "he_evaluation": he_evaluation})
    leakage_hits = []
    for entity in sample.truth_record()["entities"]:
        for candidate in _candidate_strings(entity):
            if candidate in plan_blob:
                leakage_hits.append({"label": entity["label"], "value": candidate})
    no_raw_report = {
        "sample_id": sample.sample_id,
        "raw_value_hits": leakage_hits,
        "passed": len(leakage_hits) == 0,
    }

    write_json(session_paths.reasoner_dir / "cloud_skill_output.json", plan)
    write_json(session_paths.reasoner_dir / "he_call_plan.json", plan)
    if he_evaluation is not None:
        write_json(session_paths.reasoner_dir / "manual_session_he_evaluation.json", he_evaluation)
    write_json(session_paths.reasoner_dir / "he_call_plan_schema_validation.json", schema_validation)
    write_json(session_paths.reasoner_dir / "he_call_authorization_report.json", authorization_report)
    write_json(session_paths.security_dir / "cloud_skill_output_no_raw_leakage_report.json", no_raw_report)
    write_json(
        Path(session_paths.artifact_root) / "manual_codex_session_provenance.json",
        _manual_session_provenance(plan_imported=True, paths=session_paths),
    )
    return {
        "plan": plan,
        "he_evaluation": he_evaluation,
        "schema_validation": schema_validation,
        "authorization_report": authorization_report,
        "no_raw_report": no_raw_report,
        "paths": session_paths,
    }


def run_real_cloud_reassembly(
    sample_id: str = "0",
    paths: RealCloudSessionPaths | None = None,
) -> dict[str, Any]:
    session_paths = paths or RealCloudSessionPaths()
    sanitized_payload = _load_sanitized_payload(session_paths.sanitization_dir / "sanitized_payload_examples.json")
    samples = ensure_samples()
    sample = select_sample(samples, sample_id)
    if sample.sample_id != sanitized_payload.sample_id:
        raise ValueError(
            f"Sample mismatch: real session artifacts are for {sanitized_payload.sample_id}, "
            f"but --sample-id resolved to {sample.sample_id}."
        )
    he_plan = json.loads((session_paths.reasoner_dir / "he_call_plan.json").read_text(encoding="utf-8"))
    he_evaluation_path = session_paths.reasoner_dir / "manual_session_he_evaluation.json"
    if he_evaluation_path.exists():
        he_plan["he_evaluation"] = json.loads(he_evaluation_path.read_text(encoding="utf-8"))
    vault = _build_real_vault(session_paths)
    audit_logger = AuditLogger()
    audit_logger.record(
        "local_ops",
        "real_cloud_he_plan_reused",
        sample_id=sample.sample_id,
        session_id=sanitized_payload.session_id,
        source="real_cloud_session",
    )
    he_results = execute_he_plan(
        he_plan,
        sanitized_payload.session_id,
        vault,
        artifact_dir=session_paths.reassembly_dir,
        result_store_dir=session_paths.result_store_dir,
        bundle_dir=session_paths.bundle_dir,
        key_path=session_paths.he_key,
    )
    reassembly = reassemble_results(
        sample,
        sanitized_payload,
        he_plan,
        he_results,
        audit_logger,
        artifact_dir=session_paths.reassembly_dir,
        result_store_dir=session_paths.result_store_dir,
    )
    audit_logger.write_jsonl(session_paths.security_dir / "audit_events_real.jsonl")
    write_json(
        session_paths.reassembly_dir / "real_cloud_execution_summary.json",
        {
            "sample_id": sample.sample_id,
            "actual_final_decision": reassembly["actual_final_decision"],
            "artifact_root": str(session_paths.reassembly_dir),
            "result_store_dir": str(session_paths.result_store_dir),
        },
    )
    return {
        "he_results": he_results,
        "reassembly": reassembly,
        "paths": session_paths,
    }
