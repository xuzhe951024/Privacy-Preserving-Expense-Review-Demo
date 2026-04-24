from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def ensure_parent(path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def write_json(path: str | Path, data: Any) -> Path:
    file_path = ensure_parent(path)
    file_path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return file_path


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> Path:
    file_path = ensure_parent(path)
    with file_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=False) + "\n")
    return file_path


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    file_path = ensure_parent(path)
    resolved_fieldnames = fieldnames or sorted({key for row in rows for key in row.keys()})
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return file_path


def write_markdown(path: str | Path, content: str) -> Path:
    file_path = ensure_parent(path)
    file_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return file_path


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()

