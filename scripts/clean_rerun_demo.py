from __future__ import annotations

import argparse
import json

from src.clean_rerun import CleanRerunConfig, complete_manual_session, run_fresh_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean generated demo outputs and rerun the demo from a fresh local state.")
    parser.add_argument("--mode", choices=["fresh", "manual-complete"], default="fresh")
    parser.add_argument("--sample-id", default="0")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--benchmark-iterations", type=int, default=5)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--expect-gpu", action="store_true")
    parser.add_argument("--skip-benchmark", action="store_true")
    parser.add_argument("--purge-model-cache", action="store_true")
    parser.add_argument("--manual-plan", default="real_cloud_session/handoff/session_output/cloud_skill_output.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.mode == "fresh":
        result = run_fresh_demo(
            CleanRerunConfig(
                sample_id=args.sample_id,
                threshold=args.threshold,
                device=args.device,
                n=args.n,
                seed=args.seed,
                benchmark_iterations=args.benchmark_iterations,
                progress_every=args.progress_every,
                expect_gpu=args.expect_gpu,
                skip_benchmark=args.skip_benchmark,
                purge_model_cache=args.purge_model_cache,
                dry_run=args.dry_run,
            )
        )
    else:
        result = complete_manual_session(
            sample_id=args.sample_id,
            manual_plan=args.manual_plan,
            dry_run=args.dry_run,
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
