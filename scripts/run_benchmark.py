from __future__ import annotations

import argparse
import time

from src.demo_workflow import detect_sample, run_demo_flow
from src.pipeline import load_samples_from_truth, select_sample
from src.report_writer import write_csv, write_markdown
from src.runtime_env import collect_torch_runtime, resolve_runtime_device
from src.sanitizer import sanitize_sample
from src.synthetic_data import generate_samples, save_dataset
from src.vault import Vault


def ensure_samples() -> list:
    samples = load_samples_from_truth("data/synthetic_ground_truth.jsonl")
    if samples:
        return samples
    generated = generate_samples(1000, 42)
    save_dataset(generated, "data/synthetic_expenses.jsonl", "data/synthetic_ground_truth.jsonl", "demo_artifacts/09_validation")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight latency benchmarks.")
    parser.add_argument("--sample-id", default="0")
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()

    samples = ensure_samples()
    sample = select_sample(samples, args.sample_id)
    vault = Vault(".local/benchmark_vault.key", ".local/benchmark_vault.sqlite")
    runtime = resolve_runtime_device("auto")
    torch_runtime = collect_torch_runtime()
    gpu_enabled = runtime["resolved_device"] == "cuda"
    if torch_runtime["installed"]:
        import torch  # type: ignore
    else:
        torch = None  # type: ignore[assignment]

    rows = []
    for phase in ["rule_plus_gliner", "sanitizer", "vault_roundtrip", "e2e"]:
        timings = []
        gpu_peak_mb = []
        for iteration in range(args.iterations):
            if gpu_enabled and torch is not None:
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
            start = time.perf_counter()
            if phase == "rule_plus_gliner":
                detect_sample(sample)
            elif phase == "sanitizer":
                detection = detect_sample(sample)
                sanitize_sample(sample, detection["resolved_entities"], vault, artifact_dir=".local/benchmark_artifacts")
            elif phase == "vault_roundtrip":
                detection = detect_sample(sample)
                payload = sanitize_sample(sample, detection["resolved_entities"], vault, artifact_dir=".local/benchmark_artifacts")
                for token in payload.metadata:
                    vault.get_secret(payload.session_id, token)
            elif phase == "e2e":
                run_demo_flow(sample, vault=vault, artifact_root=".local/benchmark_artifacts/e2e")
            if gpu_enabled and torch is not None:
                torch.cuda.synchronize()
                gpu_peak_mb.append(round(torch.cuda.max_memory_allocated() / (1024 * 1024), 3))
            timings.append((time.perf_counter() - start) * 1000)
        rows.append(
            {
                "phase": phase,
                "device": runtime["resolved_device"].upper(),
                "iterations": args.iterations,
                "avg_latency_ms": round(sum(timings) / len(timings), 3),
                "max_latency_ms": round(max(timings), 3),
                "min_latency_ms": round(min(timings), 3),
                "text_length": len(sample.raw_text),
                "gpu_memory_peak_mb": round(max(gpu_peak_mb), 3) if gpu_peak_mb else 0.0,
            }
        )

    gpu_rows = rows if gpu_enabled else [{"phase": "all", "device": "GPU", "status": "unavailable_or_not_configured"}]
    write_csv("demo_artifacts/07_performance/latency_cpu.csv", rows)
    write_csv("demo_artifacts/07_performance/latency_gpu.csv", gpu_rows)
    write_markdown(
        "demo_artifacts/07_performance/benchmark_summary.md",
        "\n".join(
            [
                "# Benchmark Summary",
                "",
                f"- Sample ID: {sample.sample_id}",
                f"- Iterations per phase: {args.iterations}",
                f"- Resolved device: {runtime['resolved_device']}",
                f"- Runtime reason: {runtime['reason']}",
                "- The benchmark records GPU peak memory when CUDA is active.",
            ]
        ),
    )
    print("Benchmark artifacts written to demo_artifacts/07_performance.")


if __name__ == "__main__":
    main()
