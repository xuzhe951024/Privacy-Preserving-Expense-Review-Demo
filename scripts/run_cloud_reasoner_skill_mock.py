from __future__ import annotations

import argparse

from src.cloud_reasoner_client import run_cloud_skill_mock


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the isolated cloud reasoner skill mock.")
    parser.add_argument("--bundle", default="cloud_session_bundle")
    args = parser.parse_args()
    result = run_cloud_skill_mock(bundle_dir=args.bundle)
    print(
        f"Cloud skill decision: {result['cloud_response']['decision']}; "
        f"schema_valid={result['he_plan_validation']['valid']}; "
        f"authorized={result['authorization_report']['authorized']}"
    )


if __name__ == "__main__":
    main()

