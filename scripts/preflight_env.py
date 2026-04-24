from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from src.report_writer import write_json, write_markdown
from src.runtime_env import collect_torch_runtime, ensure_local_runtime_dirs, gliner_is_installed, resolve_runtime_device


def run_command(command: str) -> dict[str, str | int]:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return {"command": command, "returncode": result.returncode, "output": output}

def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a read-only environment report.")
    parser.add_argument("--expect-gpu", action="store_true")
    args = parser.parse_args()

    artifact_root = Path("demo_artifacts/00_env")
    cache_paths = ensure_local_runtime_dirs(".")
    commands = [
        "uname -a",
        "uname -m",
        "lsb_release -a || cat /etc/os-release",
        "which uv || true",
        "uv --version || true",
        "which python3 || true",
        "python3 --version || true",
        "which nvidia-smi || true",
        "nvidia-smi || true",
        "which docker || true",
        "docker --version || true",
    ]
    results = [run_command(command) for command in commands]
    torch_status = collect_torch_runtime()
    device_resolution = resolve_runtime_device("auto")
    recommended_mode = "gpu_default" if device_resolution["resolved_device"] == "cuda" else "cpu_fallback"

    compatibility_matrix = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "uv_available": any(item["command"] == "which uv || true" and item["output"] for item in results),
        "torch_installed": torch_status["installed"],
        "torch_cuda_available": torch_status["cuda_available"],
        "torch_version": torch_status["torch_version"],
        "torch_cuda_version": torch_status["cuda_version"],
        "gpu_device_names": torch_status["device_names"],
        "gliner_installed": gliner_is_installed(),
        "resolved_device": device_resolution["resolved_device"],
        "recommended_mode": recommended_mode,
        "local_cache_paths": cache_paths,
        "notes": [
            "The demo runs in a local virtual environment managed by uv.",
            "The default runtime prefers GPU when CUDA is available and falls back to CPU otherwise.",
            "No system Python, driver, Docker, or service configuration changes were performed by this script.",
        ],
    }
    torch_cuda_check = "\n".join(
        [
            "Torch CUDA Check",
            f"Installed: {torch_status['installed']}",
            f"CUDA available: {torch_status['cuda_available']}",
            f"Detail: {torch_status['detail']}",
            f"Resolved device: {device_resolution['resolved_device']}",
            f"Reason: {device_resolution['reason']}",
            f"GLiNER installed: {gliner_is_installed()}",
        ]
    )

    markdown_lines = [
        "# Environment Report",
        "",
        "## Summary",
        "",
        f"- Recommended mode: `{recommended_mode}`",
        f"- Architecture: `{platform.machine()}`",
        f"- Python: `{platform.python_version()}`",
        f"- uv available: `{compatibility_matrix['uv_available']}`",
        f"- torch installed: `{torch_status['installed']}`",
        f"- torch CUDA available: `{torch_status['cuda_available']}`",
        f"- resolved runtime device: `{device_resolution['resolved_device']}`",
        f"- GLiNER installed: `{gliner_is_installed()}`",
        "",
        "## Command Output",
        "",
    ]
    for result in results:
        markdown_lines.extend(
            [
                f"### `{result['command']}`",
                "",
                "```text",
                str(result["output"] or "<no output>"),
                "```",
                "",
            ]
        )
    markdown_lines.extend(
        [
            "## Isolation Statement",
            "",
            "- The demo uses an isolated project environment.",
            "- This preflight script is read-only and does not modify system configuration.",
            "- The default runtime is GPU-first when CUDA is available. CPU fallback stays available.",
        ]
    )

    write_markdown(artifact_root / "env_report.md", "\n".join(markdown_lines))
    write_json(artifact_root / "compatibility_matrix.json", compatibility_matrix)
    (artifact_root / "torch_cuda_check.txt").write_text(torch_cuda_check + "\n", encoding="utf-8")
    if args.expect_gpu and device_resolution["resolved_device"] != "cuda":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
