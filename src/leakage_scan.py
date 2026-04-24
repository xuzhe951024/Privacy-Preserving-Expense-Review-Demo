from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CRYPTO_FIELD_NAMES = {
    "ciphertext",
    "ciphertext_negative_value",
    "ciphertext_reference_minus_window",
    "n",
    "g",
}


def remove_crypto_material(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<CRYPTO_MATERIAL>" if key in CRYPTO_FIELD_NAMES else remove_crypto_material(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [remove_crypto_material(item) for item in value]
    return value


def safe_json_text_for_leakage_scan(value: Any) -> str:
    return json.dumps(remove_crypto_material(value), sort_keys=True)


def safe_file_text_for_leakage_scan(path: str | Path) -> str:
    file_path = Path(path)
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return file_path.read_text(encoding="utf-8")
    return safe_json_text_for_leakage_scan(payload)
