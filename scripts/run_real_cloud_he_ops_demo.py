from __future__ import annotations

import argparse

from src.real_cloud_session import run_real_cloud_reassembly


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Paillier HE result decryption and reassembly for the manual Codex session path.")
    parser.add_argument("--sample-id", default="0")
    args = parser.parse_args()

    result = run_real_cloud_reassembly(sample_id=args.sample_id)
    print(f"Manual Codex session Paillier HE demo finished. Final decision: {result['reassembly']['actual_final_decision']}")


if __name__ == "__main__":
    main()
