# Privacy-Preserving Expense Review Assistant

## What this demo proves

This repository demonstrates a privacy-preserving enterprise expense review workflow with strict local/cloud boundaries.

- Sensitive fields are detected locally.
- Raw values are replaced with placeholders and encrypted into a local vault.
- The repository-internal baseline reasoner sees only sanitized payloads, public policy summaries, and Paillier ciphertext handles.
- The cloud skill can request only allowlisted Paillier HE operations over encrypted placeholder handles.
- Final policy evaluation and plaintext recovery happen locally with audit traces and correctness reports.

## Architecture

The demo is organized into four execution zones:

1. Local input, detection, and sanitization.
2. Cloud bundle export and cloud-side skill reasoning.
3. Paillier public-key HE operation planning and encrypted-handle execution.
4. Local decryption, reassembly, policy evaluation, and auditing.

Generated showcase assets live under `demo_artifacts/`.

## Quick Start With uv

The default path is GPU-first. If CUDA is available, the demo will prefer GPU automatically. If CUDA is unavailable, the same environment falls back to CPU.

```bash
uv --cache-dir /tmp/uv-cache sync
uv --cache-dir /tmp/uv-cache run python scripts/preflight_env.py --expect-gpu
uv --cache-dir /tmp/uv-cache run python scripts/gen_synthetic_data.py --n 1000 --seed 42
uv --cache-dir /tmp/uv-cache run python scripts/run_eval.py --threshold 0.3 --device auto
uv --cache-dir /tmp/uv-cache run python scripts/run_e2e_demo.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/export_cloud_session_bundle.py --sample-id 0 --prepare-handoff
uv --cache-dir /tmp/uv-cache run python scripts/run_cloud_reasoner_skill_mock.py --bundle cloud_session_bundle
uv --cache-dir /tmp/uv-cache run python scripts/import_cloud_he_plan.py --plan demo_artifacts/04_reasoner/he_call_plan.json
uv --cache-dir /tmp/uv-cache run python scripts/run_he_ops_demo.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/run_leakage_test.py
uv --cache-dir /tmp/uv-cache run python scripts/run_correctness_suite.py --n 1000 --seed 42 --threshold 0.3 --device auto
uv --cache-dir /tmp/uv-cache run streamlit run app/streamlit_app.py
```

## CPU Mode

The default installation is GPU-ready. CPU fallback happens automatically at runtime if CUDA is not available or if the GLiNER GPU path fails.

## Default GPU Mode

The project installs CUDA-enabled PyTorch wheels by default and stores Hugging Face and torch caches under `.local/`. The repository never modifies drivers, Docker runtime settings, or system services.

## Full Pipeline Run

```bash
uv --cache-dir /tmp/uv-cache sync
uv --cache-dir /tmp/uv-cache run python scripts/preflight_env.py --expect-gpu
uv --cache-dir /tmp/uv-cache run python scripts/gen_synthetic_data.py --n 1000 --seed 42
uv --cache-dir /tmp/uv-cache run python scripts/run_eval.py --threshold 0.3 --device auto
uv --cache-dir /tmp/uv-cache run python scripts/run_e2e_demo.py --sample-id 0 --device auto
uv --cache-dir /tmp/uv-cache run python scripts/export_cloud_session_bundle.py --sample-id 0 --device auto --prepare-handoff
uv --cache-dir /tmp/uv-cache run python scripts/run_cloud_reasoner_skill_mock.py --bundle cloud_session_bundle
uv --cache-dir /tmp/uv-cache run python scripts/import_cloud_he_plan.py --plan demo_artifacts/04_reasoner/he_call_plan.json
uv --cache-dir /tmp/uv-cache run python scripts/run_he_ops_demo.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/run_leakage_test.py --sample-id 0
uv --cache-dir /tmp/uv-cache run python scripts/run_benchmark.py --sample-id 0 --iterations 5
uv --cache-dir /tmp/uv-cache run python scripts/run_correctness_suite.py --n 1000 --seed 42 --threshold 0.3 --device auto
```

## One-Command Clean Rerun

To remove generated outputs and rebuild the repository-internal reasoner path plus the manual second-session handoff package in one command:

```bash
./clean_rerun.py --mode fresh --sample-id 0 --device auto --expect-gpu
```

This `fresh` mode clears generated demo outputs and runtime state, then reruns:

- environment preflight
- synthetic data generation
- detection evaluation
- the local end-to-end path with the repository-internal reasoner
- repository-internal baseline reasoner bundle export and validation
- leakage, benchmark, and correctness checks
- manual second-session package preparation under `real_cloud_session/handoff/`

After the second Codex session writes `real_cloud_session/handoff/session_output/cloud_skill_output.json`, complete the manual-session path with:

```bash
./clean_rerun.py --mode manual-complete --sample-id 0 --manual-plan real_cloud_session/handoff/session_output/cloud_skill_output.json
```

Use `--dry-run` to preview which paths will be deleted and which commands will run.
Use `--purge-model-cache` only if you also want to delete the local Hugging Face and torch caches under `.local/`.
The command prints each pipeline step as it runs. For a quicker smoke run, use `--n 64 --skip-benchmark --progress-every 8`; for the full demo, keep the default `--n 1000`.

The most useful artifacts to review after the run are:

- `demo_artifacts/00_env/env_report.md`
- `demo_artifacts/02_detection/detection_metrics_by_entity.csv`
- `demo_artifacts/03_sanitization/sanitized_payload_examples.json`
- `demo_artifacts/04_reasoner/he_call_plan.json`
- `demo_artifacts/05_reassembly/final_user_visible_results.md`
- `demo_artifacts/06_security/leakage_report.json`
- `demo_artifacts/09_validation/result_correctness_summary.md`

## Manual Codex Session Simulation

To demonstrate the cloud boundary with a separate Codex session while keeping its outputs clearly distinguishable from the repository-internal mock path:

```bash
uv --cache-dir /tmp/uv-cache run python scripts/prepare_real_cloud_session.py --sample-id 0 --device auto
```

This generates a dedicated manual-session tree:

- `real_cloud_session/bundle/`
- `real_cloud_session/handoff/`
- `demo_artifacts/10_real_cloud_session/`
- `.secrets/real_cloud_session/`
- `.local/real_cloud_session/`

Manual workflow:

1. Open a second Codex session rooted at `real_cloud_session/handoff/` only.
2. In that second session, follow `OPEN_IN_SECOND_SESSION.md`.
3. Have the second session write `session_output/he_call_plan.json`, then run `python3 tools/run_real_he_eval.py --plan session_output/he_call_plan.json --output session_output/cloud_skill_output.json`.
4. Back in the main repository, import and validate the returned plan into the real-session artifact root:

```bash
uv --cache-dir /tmp/uv-cache run python scripts/import_real_cloud_he_plan.py --plan real_cloud_session/handoff/session_output/cloud_skill_output.json
uv --cache-dir /tmp/uv-cache run python scripts/run_real_cloud_he_ops_demo.py --sample-id 0
```

This keeps the second session isolated from the vault, local secrets, raw source text, and the rest of the repository, while also keeping the manual-session outputs clearly distinct from the mock artifacts.
The manual-session local vault and Paillier private key material are also isolated from the mock path under `.secrets/real_cloud_session/` and `.local/real_cloud_session/`.
These manual-session runtime directories are git-ignored so they cannot be accidentally committed together with the tracked mock showcase artifacts.
The separation here is for both boundary control and provenance clarity: the manual second-session result should never be mistaken for the repository-internal mock result.

## UI

Launch the Streamlit app with:

```bash
uv --cache-dir /tmp/uv-cache run streamlit run app/streamlit_app.py
```

The app now binds to `0.0.0.0:8501` by default. You can open it locally at `http://127.0.0.1:8501`, or over Tailscale at `http://<your-tailscale-ip>:8501` or `http://<your-magicdns-name>:8501`.

The UI is split into two fully separated pages:

- `Mock Cloud Session Demo`: reads only the repository-internal mock artifacts.
- `Manual Codex Session Simulation`: reads only `real_cloud_session/` and `demo_artifacts/10_real_cloud_session/`.

The most important mock-page tabs are:

1. `Raw Local Input`
2. `Local Detection & Sanitization`
3. `Cloud Bundle Preview`
4. `Cloud Skill Output`
5. `HE Ops Trace`
6. `Local Decryption & Final Result`
7. `Security & Correctness Dashboard`

The manual-session page presents:

1. The dedicated manual-session bundle and handoff package
2. The imported plan returned by the second Codex session
3. The manual-session Paillier HE execution and reassembly results
4. The manual-session no-raw-leakage and audit reports

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
- Cloud bundle exports include hashes and Paillier public-key ciphertexts, not vault contents or private keys.
- HE calls are schema-validated and authorization-checked.
- The second Codex session must run the bundled Paillier evaluator tool to produce encrypted HE results.
- Unsafe requests such as `decrypt`, `reveal`, `lookup_vault`, and `print_raw` are rejected.

## Known Limitations

- If the GLiNER model download fails, the repository degrades to the heuristic fallback detector instead of disabling the full demo.
- The HE layer uses a real Paillier additive homomorphic scheme for encrypted sums and policy deltas, but it is not a production KMS/HSM deployment.
- Policy comparison is completed locally after decrypting an encrypted delta; the cloud side does not decrypt or learn the plaintext amount.
- The repository does not implement OCR, real cloud LLM API calls, or full FHE inference.

## References

- uv Working on Projects
- uv with PyTorch
- PyTorch Get Started Locally
- NVIDIA Container Toolkit Install Guide
- NVIDIA GLiNER-PII model card
- Microsoft Presidio entity references
- ACL 2025 re-identification paper
- Paillier cryptosystem
