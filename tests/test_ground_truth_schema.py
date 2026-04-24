from __future__ import annotations

from jsonschema import Draft202012Validator

from src.ground_truth_schema import build_ground_truth_schema
from src.synthetic_data import generate_samples


def test_generated_ground_truth_matches_schema():
    validator = Draft202012Validator(build_ground_truth_schema())
    for sample in generate_samples(12, 42):
        record = sample.truth_record()
        validator.validate(record)
        for entity in sample.entities:
            assert sample.raw_text[entity.start:entity.end] == entity.text

