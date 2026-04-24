from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.cloud_reasoner_client import validate_against_schema
from src.cloud_reasoner_mock import validate_authorized_he_ops
from src.report_writer import write_json


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and import a cloud-produced HE call plan.")
    parser.add_argument("--plan", default="demo_artifacts/04_reasoner/he_call_plan.json")
    parser.add_argument("--bundle", default="cloud_session_bundle")
    args = parser.parse_args()

    plan = load_json(args.plan)
    metadata = load_json(Path(args.bundle) / "placeholder_metadata.json")
    schema_validation = validate_against_schema(plan, "skills/privacy_expense_cloud_reasoner/schemas/he_call_plan.schema.json")
    authorization_report = validate_authorized_he_ops(plan, metadata)
    write_json("demo_artifacts/04_reasoner/he_call_plan_schema_validation.json", schema_validation)
    write_json("demo_artifacts/04_reasoner/he_call_authorization_report.json", authorization_report)
    print(f"Plan validation complete: schema_valid={schema_validation['valid']}, authorized={authorization_report['authorized']}")


if __name__ == "__main__":
    main()

