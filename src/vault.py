from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.report_writer import sha256_text


class Vault:
    def __init__(self, key_path: str | Path = ".secrets/vault.key", db_path: str | Path = ".local/vault.sqlite") -> None:
        self.key_path = Path(key_path)
        self.db_path = Path(db_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_entries (
                    session_id TEXT NOT NULL,
                    token TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    source_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, token)
                )
                """
            )

    def _load_key(self) -> bytes:
        if not self.key_path.exists():
            self.key_path.write_bytes(os.urandom(32))
            os.chmod(self.key_path, 0o600)
        return self.key_path.read_bytes()

    def put_secret(
        self,
        session_id: str,
        token: str,
        entity_type: str,
        raw_value: str,
        normalized_value: str | None = None,
    ) -> dict[str, Any]:
        aes = AESGCM(self._load_key())
        nonce = os.urandom(12)
        payload = json.dumps({"raw_value": raw_value, "normalized_value": normalized_value}).encode("utf-8")
        ciphertext = aes.encrypt(nonce, payload, associated_data=f"{session_id}:{token}:{entity_type}".encode("utf-8"))
        record = (
            session_id,
            token,
            entity_type,
            nonce,
            ciphertext,
            sha256_text(raw_value),
            datetime.now(timezone.utc).isoformat(),
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO vault_entries (
                    session_id, token, entity_type, nonce, ciphertext, source_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                record,
            )
        return {
            "token": token,
            "entity_type": entity_type,
            "source_hash_prefix": sha256_text(raw_value)[:12],
            "recoverable": True,
        }

    def get_secret(self, session_id: str, token: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT entity_type, nonce, ciphertext FROM vault_entries WHERE session_id = ? AND token = ?",
                (session_id, token),
            ).fetchone()
        if row is None:
            raise KeyError(f"Missing vault token: {token}")
        entity_type, nonce, ciphertext = row
        aes = AESGCM(self._load_key())
        decrypted = aes.decrypt(
            nonce,
            ciphertext,
            associated_data=f"{session_id}:{token}:{entity_type}".encode("utf-8"),
        )
        payload = json.loads(decrypted.decode("utf-8"))
        return {
            "token": token,
            "entity_type": entity_type,
            "raw_value": payload["raw_value"],
            "normalized_value": payload.get("normalized_value"),
        }

    def list_session_records(self, session_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT token, entity_type, source_hash, created_at FROM vault_entries WHERE session_id = ? ORDER BY token",
                (session_id,),
            ).fetchall()
        return [
            {
                "token": token,
                "entity_type": entity_type,
                "source_hash_prefix": source_hash[:12],
                "created_at": created_at,
                "recoverable": True,
            }
            for token, entity_type, source_hash, created_at in rows
        ]

    def count_session_records(self, session_id: str) -> int:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM vault_entries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row[0]) if row else 0

