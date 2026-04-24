from __future__ import annotations


def describe_tfhe_placeholder() -> dict[str, str]:
    return {
        "status": "placeholder_only",
        "message": "The repository includes a mock HE service. Real TFHE-rs integration is intentionally out of scope for the default path.",
    }

