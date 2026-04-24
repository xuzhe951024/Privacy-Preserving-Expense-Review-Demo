from __future__ import annotations

import random
from pathlib import Path

import pytest

from src.synthetic_data import build_client_dinner, build_missing_policy_cap, build_missing_receipt


@pytest.fixture()
def sample_client_dinner():
    return build_client_dinner(0, random.Random(42), amount=482.15)


@pytest.fixture()
def sample_within_cap():
    return build_client_dinner(1, random.Random(7), amount=430.00)


@pytest.fixture()
def sample_at_cap():
    return build_client_dinner(2, random.Random(9), amount=450.00)


@pytest.fixture()
def sample_missing_receipt():
    return build_missing_receipt(3, random.Random(11))


@pytest.fixture()
def sample_missing_policy():
    return build_missing_policy_cap(4, random.Random(13))


@pytest.fixture()
def temp_artifact_root(tmp_path: Path) -> Path:
    return tmp_path

