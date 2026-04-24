from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any


def ensure_local_runtime_dirs(project_root: str | Path = ".") -> dict[str, str]:
    root = Path(project_root)
    local_root = root / ".local"
    hf_home = local_root / "hf-home"
    torch_home = local_root / "torch-home"
    hf_hub_cache = hf_home / "hub"
    transformers_cache = hf_home / "transformers"
    for path in [local_root, hf_home, torch_home, hf_hub_cache, transformers_cache]:
        path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home.resolve()))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_hub_cache.resolve()))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(transformers_cache.resolve()))
    os.environ.setdefault("TORCH_HOME", str(torch_home.resolve()))
    return {
        "local_root": str(local_root.resolve()),
        "hf_home": str(hf_home.resolve()),
        "hf_hub_cache": str(hf_hub_cache.resolve()),
        "transformers_cache": str(transformers_cache.resolve()),
        "torch_home": str(torch_home.resolve()),
    }


def torch_is_installed() -> bool:
    return importlib.util.find_spec("torch") is not None


def gliner_is_installed() -> bool:
    return importlib.util.find_spec("gliner") is not None


def collect_torch_runtime() -> dict[str, Any]:
    if not torch_is_installed():
        return {
            "installed": False,
            "cuda_available": False,
            "torch_version": None,
            "cuda_version": None,
            "device_count": 0,
            "device_names": [],
            "detail": "torch is not installed in the current environment.",
        }

    import torch  # type: ignore

    cuda_available = bool(torch.cuda.is_available())
    device_count = int(torch.cuda.device_count()) if cuda_available else 0
    device_names = [torch.cuda.get_device_name(index) for index in range(device_count)] if cuda_available else []
    detail = f"torch={torch.__version__}, cuda_available={cuda_available}"
    if cuda_available:
        detail += f", cuda_version={torch.version.cuda}, device_count={device_count}"
    return {
        "installed": True,
        "cuda_available": cuda_available,
        "torch_version": torch.__version__,
        "cuda_version": getattr(torch.version, "cuda", None),
        "device_count": device_count,
        "device_names": device_names,
        "detail": detail,
    }


def resolve_runtime_device(requested_device: str = "auto") -> dict[str, Any]:
    requested = (requested_device or "auto").lower()
    torch_runtime = collect_torch_runtime()

    if requested in {"cuda", "gpu"}:
        requested = "cuda"
    if requested.startswith("cuda"):
        if torch_runtime["cuda_available"]:
            return {
                **torch_runtime,
                "requested_device": requested_device,
                "resolved_device": requested,
                "default_mode": "gpu",
                "reason": "CUDA was explicitly requested and is available.",
            }
        return {
            **torch_runtime,
            "requested_device": requested_device,
            "resolved_device": "cpu",
            "default_mode": "cpu_fallback",
            "reason": "CUDA was requested but is unavailable. Falling back to CPU.",
        }

    if requested == "cpu":
        return {
            **torch_runtime,
            "requested_device": requested_device,
            "resolved_device": "cpu",
            "default_mode": "cpu",
            "reason": "CPU was explicitly requested.",
        }

    if torch_runtime["cuda_available"]:
        return {
            **torch_runtime,
            "requested_device": requested_device,
            "resolved_device": "cuda",
            "default_mode": "gpu_default",
            "reason": "Auto mode selected CUDA because a compatible GPU is available.",
        }

    return {
        **torch_runtime,
        "requested_device": requested_device,
        "resolved_device": "cpu",
        "default_mode": "cpu_fallback",
        "reason": "Auto mode selected CPU because CUDA is unavailable.",
    }

