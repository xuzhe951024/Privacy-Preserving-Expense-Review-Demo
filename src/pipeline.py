from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import ExpenseSample
from src.report_writer import write_markdown


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_samples_from_truth(path: str | Path) -> list[ExpenseSample]:
    return [ExpenseSample.from_truth_record(record) for record in read_jsonl(path)]


def select_sample(samples: list[ExpenseSample], sample_id_or_index: str | int) -> ExpenseSample:
    if isinstance(sample_id_or_index, int):
        return samples[sample_id_or_index]
    if sample_id_or_index.isdigit():
        return samples[int(sample_id_or_index)]
    for sample in samples:
        if sample.sample_id == sample_id_or_index:
            return sample
    raise KeyError(f"Unknown sample identifier: {sample_id_or_index}")


def write_showcase_docs(root: str | Path = ".") -> None:
    project_root = Path(root)
    showcase_root = project_root / "demo_artifacts" / "08_showcase"
    write_markdown(
        showcase_root / "demo_script.md",
        "\n".join(
            [
                "# Demo Script",
                "",
                "## Phase-by-phase showcase",
                "",
                "- Phase 0: Show `demo_artifacts/00_env/env_report.md` to prove isolated environment usage and CPU fallback.",
                "- Phase 1: Show `demo_artifacts/01_data/dataset_preview.md` to explain that the dataset is fully synthetic.",
                "- Phase 2: Show `demo_artifacts/02_detection/detection_metrics_by_entity.csv` and `threshold_sweep.csv` to explain detector coverage and precision/recall tradeoffs.",
                "- Phase 3: Show `demo_artifacts/03_sanitization/sanitized_payload_examples.json` and `no_raw_leakage_check.json` to prove sanitized-only cloud requests.",
                "- Phase 4: Show `cloud_session_bundle/` and `demo_artifacts/04_reasoner/he_call_plan.json` to explain the cloud boundary and restricted HE planning.",
                "- Phase 5: Show `demo_artifacts/05_reassembly/he_ops_local_decryption_report.json` and `final_user_visible_results.md` to explain that only the local side sees decrypted outcomes.",
                "- Phase 6: Show `demo_artifacts/06_security/leakage_report.json` and `audit_events.jsonl` to prove leakage testing and audit completeness.",
                "- Phase 7: Walk through the Streamlit tabs to contrast local raw input, cloud bundle preview, HE trace, and final local result.",
                "",
                "## 90-second narration",
                "",
                "1. On the left is the raw local expense text with names, employee IDs, amounts, card last four, and email addresses.",
                "2. The local detector identifies strong-format fields with rules and uses a GLiNER-compatible fallback for names and vendors.",
                "3. The system stores raw values in the local vault, replaces them with placeholders, and proves the outbound payload has zero raw leakage.",
                "4. The Cloud Bundle panel shows what an isolated cloud session actually receives: sanitized text, placeholder metadata, and public policy summaries only.",
                "5. The cloud skill can only return a HE tool-call plan such as comparing `AMOUNT_1` against a policy cap and requesting an encrypted delta.",
                "6. The HE trace shows that the cloud sees encrypted input handles and encrypted result handles, not plaintext amounts.",
                "7. Only the local side decrypts the result handles and combines them with local policy logic to produce the final routing decision.",
                "8. The dashboard shows no raw leakage, no unauthorized cloud ops, and final decision correctness against a synthetic oracle.",
            ]
        ),
    )
    write_markdown(
        showcase_root / "ui_walkthrough.md",
        "\n".join(
            [
                "# UI Walkthrough",
                "",
                "- Raw Local Input: original text and workflow context.",
                "- Local Detection & Sanitization: spans, labels, scores, sources, and generated placeholders.",
                "- Cloud Bundle Preview: sanitized request, placeholder metadata, and public policy summary.",
                "- Cloud Skill Output: HE call plan, schema validation, and authorization report.",
                "- HE Ops Trace: encrypted input handles and encrypted result handles.",
                "- Local Decryption & Final Result: decrypted HE outputs and final decision summary.",
                "- Security & Correctness Dashboard: leakage report, audit trail, and correctness summary.",
            ]
        ),
    )
    write_markdown(
        showcase_root / "screenshots_placeholder.md",
        "\n".join(
            [
                "# Screenshot Placeholders",
                "",
                "- Placeholder 1: Local raw input and detected entities.",
                "- Placeholder 2: Sanitized cloud bundle preview.",
                "- Placeholder 3: HE tool-call plan and authorization report.",
                "- Placeholder 4: Final local decision and correctness dashboard.",
            ]
        ),
    )

