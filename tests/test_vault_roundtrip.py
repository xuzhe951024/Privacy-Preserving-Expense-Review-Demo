from __future__ import annotations

from src.vault import Vault


def test_vault_roundtrip(tmp_path):
    vault = Vault(tmp_path / "vault.key", tmp_path / "vault.sqlite")
    preview = vault.put_secret("session-1", "AMOUNT_1", "AMOUNT", "$482.15", "482.15")
    secret = vault.get_secret("session-1", "AMOUNT_1")
    assert preview["recoverable"] is True
    assert secret["raw_value"] == "$482.15"
    assert secret["normalized_value"] == "482.15"

