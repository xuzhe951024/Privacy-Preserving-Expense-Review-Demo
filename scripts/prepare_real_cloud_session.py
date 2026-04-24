from __future__ import annotations

import argparse

from src.real_cloud_session import prepare_real_cloud_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a fully isolated real cloud-session package.")
    parser.add_argument("--sample-id", default="0")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    result = prepare_real_cloud_session(sample_id=args.sample_id, threshold=args.threshold, device=args.device)
    print(
        f"Prepared isolated real cloud session for {result['sample'].sample_id} at "
        f"{result['paths'].handoff_dir}"
    )


if __name__ == "__main__":
    main()

