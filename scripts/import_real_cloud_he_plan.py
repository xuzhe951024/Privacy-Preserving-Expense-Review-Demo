from __future__ import annotations

import argparse

from src.real_cloud_session import import_real_cloud_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and validate a real second-session HE plan.")
    parser.add_argument("--plan", default=None)
    args = parser.parse_args()

    result = import_real_cloud_plan(plan_path=args.plan)
    print(
        f"Imported real cloud plan: schema_valid={result['schema_validation']['valid']}, "
        f"authorized={result['authorization_report']['authorized']}, "
        f"no_raw_leakage={result['no_raw_report']['passed']}"
    )


if __name__ == "__main__":
    main()

