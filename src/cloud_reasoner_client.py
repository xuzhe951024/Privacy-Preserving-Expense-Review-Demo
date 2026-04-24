from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from src.cloud_reasoner_mock import (
    build_cloud_skill_response,
    build_local_reasoner_response,
    validate_authorized_he_ops,
    write_reasoner_artifacts,
)
from src.report_writer import write_json


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_against_schema(instance: dict[str, Any], schema_path: str | Path) -> dict[str, Any]:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = [{"message": error.message, "path": list(error.path)} for error in validator.iter_errors(instance)]
    return {"schema": str(schema_path), "valid": len(errors) == 0, "errors": errors}


def run_cloud_skill_mock(
    bundle_dir: str | Path = "cloud_session_bundle",
    artifact_dir: str | Path = "demo_artifacts/04_reasoner",
    schema_root: str | Path = "skills/privacy_expense_cloud_reasoner/schemas",
) -> dict[str, Any]:
    bundle_root = Path(bundle_dir)
    artifact_root = Path(artifact_dir)
    schema_dir = Path(schema_root)
    sanitized_request = load_json(bundle_root / "sanitized_request.json")
    sanitized_request["metadata"] = load_json(bundle_root / "placeholder_metadata.json")
    sanitized_request["policy_summary"] = load_json(bundle_root / "policy_public_summary.json")
    local_response = build_local_reasoner_response(sanitized_request)
    cloud_response = build_cloud_skill_response(sanitized_request)
    authorization_report = write_reasoner_artifacts(sanitized_request, local_response, cloud_response, artifact_dir=artifact_root)
    reasoner_schema_validation = validate_against_schema(
        local_response,
        schema_dir / "cloud_reasoner_response.schema.json",
    )
    he_plan_validation = validate_against_schema(cloud_response, schema_dir / "he_call_plan.schema.json")
    write_json(artifact_root / "reasoner_schema_validation.json", reasoner_schema_validation)
    write_json(artifact_root / "he_call_plan_schema_validation.json", he_plan_validation)
    return {
        "sanitized_request": sanitized_request,
        "local_response": local_response,
        "cloud_response": cloud_response,
        "authorization_report": authorization_report,
        "reasoner_schema_validation": reasoner_schema_validation,
        "he_plan_validation": he_plan_validation,
        "he_call_authorization_report": validate_authorized_he_ops(cloud_response, sanitized_request["metadata"]),
    }

