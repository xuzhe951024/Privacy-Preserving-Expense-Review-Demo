#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    uv_cache_dir = os.environ.get("UV_CACHE_DIR", "/tmp/uv-cache")
    command = [
        "uv",
        "--cache-dir",
        uv_cache_dir,
        "run",
        "python",
        "scripts/clean_rerun_demo.py",
        *sys.argv[1:],
    ]
    return subprocess.call(command, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
