from __future__ import annotations

from pathlib import Path

from src.clean_rerun import CleanRerunConfig, fresh_run_commands, manual_complete_commands, remove_generated_outputs


def test_remove_generated_outputs_removes_known_runtime_targets(tmp_path: Path):
    (tmp_path / "cloud_session_bundle").mkdir(parents=True)
    (tmp_path / "demo_artifacts" / "04_reasoner").mkdir(parents=True)
    (tmp_path / ".local" / "he_results").mkdir(parents=True)
    (tmp_path / ".secrets").mkdir(parents=True)
    (tmp_path / ".secrets" / "vault.key").write_text("secret", encoding="utf-8")

    removed = remove_generated_outputs(root=tmp_path)

    assert "cloud_session_bundle" in removed
    assert "demo_artifacts/04_reasoner" in removed
    assert ".local/he_results" in removed
    assert ".secrets/vault.key" in removed
    assert not (tmp_path / "cloud_session_bundle").exists()
    assert not (tmp_path / "demo_artifacts" / "04_reasoner").exists()
    assert not (tmp_path / ".local" / "he_results").exists()
    assert not (tmp_path / ".secrets" / "vault.key").exists()


def test_fresh_run_commands_include_mock_and_manual_paths():
    commands = fresh_run_commands(CleanRerunConfig(expect_gpu=True, skip_benchmark=True))

    assert commands[0] == ["scripts/preflight_env.py", "--expect-gpu"]
    assert ["scripts/run_cloud_reasoner_skill_mock.py", "--bundle", "cloud_session_bundle"] in commands
    assert ["scripts/prepare_real_cloud_session.py", "--sample-id", "0", "--device", "auto"] in commands
    assert [
        "scripts/run_eval.py",
        "--threshold",
        "0.3",
        "--device",
        "auto",
        "--progress-every",
        "25",
    ] in commands


def test_manual_complete_commands_import_and_reassemble():
    commands = manual_complete_commands("0", "real_cloud_session/handoff/session_output/cloud_skill_output.json")

    assert commands == [
        ["scripts/import_real_cloud_he_plan.py", "--plan", "real_cloud_session/handoff/session_output/cloud_skill_output.json"],
        ["scripts/run_real_cloud_he_ops_demo.py", "--sample-id", "0"],
    ]
