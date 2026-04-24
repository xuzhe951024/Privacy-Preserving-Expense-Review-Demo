# Privacy-Preserving Expense Review Assistant

## What this demo proves

This repository demonstrates a privacy-preserving enterprise expense review workflow with strict local/cloud boundaries.

- Sensitive fields are detected locally.
- Raw values are replaced with placeholders and encrypted into a local vault.
- The cloud-side mock reasoner sees only sanitized payloads and public policy summaries.
- The cloud skill can request only allowlisted HE-style operations over placeholder handles.
- Final policy evaluation and plaintext recovery happen locally with audit traces and correctness reports.

## Architecture

The demo is organized into four execution zones:

1. Local input, detection, and sanitization.
2. Cloud bundle export and cloud-side skill reasoning.
3. Mock HE operation planning and encrypted-handle execution.
4. Local decryption, reassembly, policy evaluation, and auditing.

Generated showcase assets live under `demo_artifacts/`.

## Quick Start With uv

The default path is CPU-friendly and does not require a GPU.

```bash
uv --cache-dir /tmp/uv-cache sync
uv --cache-dir /tmp/uv-cache run python scripts/preflight_env.py
uv --cache-dir /tmp/uv-cache run python scripts/gen_synthetic_data.py --n 1000 --seed 42
uv --cache-dir /tmp/uv-cache run python scripts/run_eval.py --threshold 0.3 --device auto
uv --cache-dir /tmp/uv-cache run python scripts/run_e2e_demo.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/export_cloud_session_bundle.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/run_cloud_reasoner_skill_mock.py --bundle cloud_session_bundle
uv --cache-dir /tmp/uv-cache run python scripts/import_cloud_he_plan.py --plan demo_artifacts/04_reasoner/he_call_plan.json
uv --cache-dir /tmp/uv-cache run python scripts/run_he_ops_demo.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/run_leakage_test.py
uv --cache-dir /tmp/uv-cache run python scripts/run_correctness_suite.py --n 1000 --seed 42 --threshold 0.3 --device auto
uv --cache-dir /tmp/uv-cache run streamlit run app/streamlit_app.py
```

## CPU Mode

The default detector stack combines rule-based recognition with a GLiNER-compatible fallback heuristic. The repository remains functional even when the GLiNER model or PyTorch is unavailable.

## Optional GPU Mode

GPU is treated as an optional accelerator. The repository never modifies drivers, Docker runtime settings, or system services.

## Demo Walkthrough

The main walkthrough is:

1. Run `scripts/preflight_env.py`.
2. Generate synthetic data with `scripts/gen_synthetic_data.py`.
3. Evaluate detection with `scripts/run_eval.py`.
4. Run one full trace with `scripts/run_e2e_demo.py`.
5. Open `demo_artifacts/08_showcase/demo_script.md`.
6. Launch the Streamlit UI.

## Generated Artifacts

Artifacts are grouped by phase:

- `demo_artifacts/00_env/`
- `demo_artifacts/01_data/`
- `demo_artifacts/02_detection/`
- `demo_artifacts/03_sanitization/`
- `demo_artifacts/04_reasoner/`
- `demo_artifacts/05_reassembly/`
- `demo_artifacts/06_security/`
- `demo_artifacts/07_performance/`
- `demo_artifacts/08_showcase/`
- `demo_artifacts/09_validation/`

## Security Boundaries

- Raw sensitive values stay local.
- `.local/`, `.secrets/`, and `.env` are ignored by git.
- Cloud bundle exports include hashes, not vault contents.
- HE-style calls are schema-validated and authorization-checked.
- Unsafe requests such as `decrypt`, `reveal`, `lookup_vault`, and `print_raw` are rejected.

## Known Limitations

- The default path uses a GLiNER-compatible fallback heuristic unless the GLiNER model is explicitly available.
- The HE layer is a demonstrator that mimics ciphertext handles and local-only decryption semantics.
- The repository does not implement OCR, real cloud LLM calls, production KMS/HSM, or full FHE inference.

## References

- uv Working on Projects
- uv with PyTorch
- PyTorch Get Started Locally
- NVIDIA Container Toolkit Install Guide
- NVIDIA GLiNER-PII model card
- Microsoft Presidio entity references
- ACL 2025 re-identification paper
- Zama TFHE-rs documentation

