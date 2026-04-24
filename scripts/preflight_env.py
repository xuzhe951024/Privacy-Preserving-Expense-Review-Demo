from __future__ import annotations

import argparse
import importlib.util
import platform
import subprocess
import sys
from pathlib import Path

from src.report_writer import write_json, write_markdown


def run_command(command: str) -> dict[str, str | int]:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return {"command": command, "returncode": result.returncode, "output": output}


def detect_torch() -> dict[str, object]:
    if importlib.util.find_spec("torch") is None:
        return {"installed": False, "cuda_available": False, "detail": "torch is not installed in the current environment."}
    import torch  # type: ignore

    cuda_available = bool(torch.cuda.is_available())
    detail = f"torch={torch.__version__}, cuda_available={cuda_available}"
    if cuda_available:
        detail += f", device_count={torch.cuda.device_count()}"
    return {"installed": True, "cuda_available": cuda_available, "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a read-only environment report.")
    parser.parse_args()

    artifact_root = Path("demo_artifacts/00_env")
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
    torch_status = detect_torch()
    recommended_mode = "cpu"
    if torch_status["installed"] and torch_status["cuda_available"]:
        recommended_mode = "gpu_optional"

    compatibility_matrix = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "uv_available": any(item["command"] == "which uv || true" and item["output"] for item in results),
        "torch_installed": torch_status["installed"],
        "torch_cuda_available": torch_status["cuda_available"],
        "recommended_mode": recommended_mode,
        "notes": [
            "The demo runs in a local virtual environment managed by uv.",
            "CPU fallback is supported even when GPU access is blocked or torch is unavailable.",
            "No system Python, driver, Docker, or service configuration changes were performed by this script.",
        ],
    }
    torch_cuda_check = "\n".join(
        [
            "Torch CUDA Check",
            f"Installed: {torch_status['installed']}",
            f"CUDA available: {torch_status['cuda_available']}",
            f"Detail: {torch_status['detail']}",
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
            "- GPU remains optional. CPU fallback stays available.",
        ]
    )

    write_markdown(artifact_root / "env_report.md", "\n".join(markdown_lines))
    write_json(artifact_root / "compatibility_matrix.json", compatibility_matrix)
    (artifact_root / "torch_cuda_check.txt").write_text(torch_cuda_check + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

