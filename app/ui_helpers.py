from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_script(*args: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def read_json(path: str) -> dict | list | None:
    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return "Artifact not generated yet."
    return file_path.read_text(encoding="utf-8")


def render_json(path: str) -> None:
    payload = read_json(path)
    if payload is None:
        st.info("Artifact not generated yet.")
        return
    st.json(payload)


def render_text(path: str, language: str = "markdown") -> None:
    content = read_text(path)
    if language == "markdown":
        st.markdown(content)
    else:
        st.code(content, language=language)

