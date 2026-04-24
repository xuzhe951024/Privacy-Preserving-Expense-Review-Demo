from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ARTIFACT_TARGETS = [
    Path("cloud_session_bundle"),
    Path("cloud_session_handoff"),
    Path("real_cloud_session"),
    Path("demo_artifacts/00_env"),
    Path("demo_artifacts/01_data"),
    Path("demo_artifacts/02_detection"),
    Path("demo_artifacts/03_sanitization"),
    Path("demo_artifacts/04_reasoner"),
    Path("demo_artifacts/05_reassembly"),
    Path("demo_artifacts/06_security"),
    Path("demo_artifacts/07_performance"),
    Path("demo_artifacts/08_showcase"),
    Path("demo_artifacts/09_validation"),
    Path("demo_artifacts/10_real_cloud_session"),
]

RUNTIME_TARGETS = [
    Path("data/synthetic_expenses.jsonl"),
    Path("data/synthetic_ground_truth.jsonl"),
    Path(".local/vault.sqlite"),
    Path(".local/he_results"),
    Path(".local/he_results_real"),
    Path(".local/real_cloud_session"),
    Path(".local/benchmark_artifacts"),
    Path(".local/correctness_artifacts"),
    Path(".local/benchmark_vault.key"),
    Path(".local/benchmark_vault.sqlite"),
    Path(".secrets/vault.key"),
    Path(".secrets/paillier_demo_key.json"),
    Path(".secrets/real_cloud_session"),
]

MODEL_CACHE_TARGETS = [
    Path(".local/huggingface"),
    Path(".local/torch"),
]


@dataclass(slots=True)
class CleanRerunConfig:
    sample_id: str = "0"
    threshold: float = 0.3
    device: str = "auto"
    n: int = 1000
    seed: int = 42
    benchmark_iterations: int = 5
    progress_every: int = 25
    expect_gpu: bool = False
    skip_benchmark: bool = False
    purge_model_cache: bool = False
    dry_run: bool = False


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def clean_targets(purge_model_cache: bool = False) -> list[Path]:
    targets = [*ARTIFACT_TARGETS, *RUNTIME_TARGETS]
    if purge_model_cache:
        targets.extend(MODEL_CACHE_TARGETS)
    return targets


def _safe_resolve_target(root: Path, relative_path: Path) -> Path:
    resolved_root = root.resolve()
    target = (resolved_root / relative_path).resolve()
    target.relative_to(resolved_root)
    if target == resolved_root:
        raise ValueError("Refusing to remove the project root.")
    return target


def remove_generated_outputs(root: Path | None = None, purge_model_cache: bool = False, dry_run: bool = False) -> list[str]:
    repo_root = (root or project_root()).resolve()
    removed: list[str] = []
    for relative_path in clean_targets(purge_model_cache=purge_model_cache):
        target = _safe_resolve_target(repo_root, relative_path)
        if not target.exists():
            continue
        removed.append(str(relative_path))
        if dry_run:
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    return removed


def fresh_run_commands(config: CleanRerunConfig) -> list[list[str]]:
    commands: list[list[str]] = [
        ["scripts/preflight_env.py"],
        ["scripts/gen_synthetic_data.py", "--n", str(config.n), "--seed", str(config.seed)],
        [
            "scripts/run_eval.py",
            "--threshold",
            str(config.threshold),
            "--device",
            config.device,
            "--progress-every",
            str(config.progress_every),
        ],
        ["scripts/run_e2e_demo.py", "--sample-id", config.sample_id, "--device", config.device],
        ["scripts/export_cloud_session_bundle.py", "--sample-id", config.sample_id, "--device", config.device, "--prepare-handoff"],
        ["scripts/run_cloud_reasoner_skill_mock.py", "--bundle", "cloud_session_bundle"],
        ["scripts/import_cloud_he_plan.py", "--plan", "demo_artifacts/04_reasoner/he_call_plan.json"],
        ["scripts/run_he_ops_demo.py", "--sample-id", config.sample_id],
        ["scripts/run_leakage_test.py", "--sample-id", config.sample_id],
        [
            "scripts/run_correctness_suite.py",
            "--n",
            str(config.n),
            "--seed",
            str(config.seed),
            "--threshold",
            str(config.threshold),
            "--device",
            config.device,
            "--progress-every",
            str(config.progress_every),
        ],
        ["scripts/prepare_real_cloud_session.py", "--sample-id", config.sample_id, "--device", config.device],
    ]
    if config.expect_gpu:
        commands[0].append("--expect-gpu")
    if not config.skip_benchmark:
        commands.insert(
            9,
            ["scripts/run_benchmark.py", "--sample-id", config.sample_id, "--iterations", str(config.benchmark_iterations)],
        )
    return commands


def manual_complete_commands(sample_id: str, manual_plan: str) -> list[list[str]]:
    return [
        ["scripts/import_real_cloud_he_plan.py", "--plan", manual_plan],
        ["scripts/run_real_cloud_he_ops_demo.py", "--sample-id", sample_id],
    ]


def _run_script(command: list[str], root: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, *command],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    output_lines: list[str] = []
    for line in process.stdout:
        output_lines.append(line.rstrip())
        print(line, end="", flush=True)
    returncode = process.wait()
    if returncode != 0:
        tail = "\n".join(output_lines[-40:])
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{tail}")


def run_fresh_demo(config: CleanRerunConfig, root: Path | None = None) -> dict[str, object]:
    repo_root = (root or project_root()).resolve()
    removed = remove_generated_outputs(
        root=repo_root,
        purge_model_cache=config.purge_model_cache,
        dry_run=config.dry_run,
    )
    commands = fresh_run_commands(config)
    if config.dry_run:
        return {
            "mode": "fresh",
            "removed": removed,
            "commands": commands,
        }
    print(f"Cleaned {len(removed)} generated paths.", flush=True)
    outputs = []
    total = len(commands)
    for index, command in enumerate(commands, start=1):
        print(f"\n[{index}/{total}] Running: {sys.executable} {' '.join(command)}", flush=True)
        _run_script(command, repo_root)
        outputs.append({"command": command, "status": "completed"})
    return {
        "mode": "fresh",
        "removed": removed,
        "commands": commands,
        "outputs": outputs,
        "manual_next_step": "Open a second Codex session rooted at real_cloud_session/handoff/ and produce session_output/cloud_skill_output.json.",
    }


def complete_manual_session(sample_id: str, manual_plan: str, dry_run: bool = False, root: Path | None = None) -> dict[str, object]:
    repo_root = (root or project_root()).resolve()
    commands = manual_complete_commands(sample_id=sample_id, manual_plan=manual_plan)
    if dry_run:
        return {
            "mode": "manual-complete",
            "commands": commands,
        }
    outputs = []
    total = len(commands)
    for index, command in enumerate(commands, start=1):
        print(f"\n[{index}/{total}] Running: {sys.executable} {' '.join(command)}", flush=True)
        _run_script(command, repo_root)
        outputs.append({"command": command, "status": "completed"})
    return {
        "mode": "manual-complete",
        "commands": commands,
        "outputs": outputs,
    }
