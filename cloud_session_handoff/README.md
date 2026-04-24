# Isolated Cloud Session Handoff

This directory is the minimal package for a second Codex session that simulates the cloud-side reasoner.

- It includes only the sanitized bundle, the cloud-side skill, and an output folder.
- It includes a Paillier public-key HE evaluator tool that can operate on ciphertexts without plaintext or private keys.
- It must not be given access to the local vault, local secrets, raw source text, or the rest of the repository.
- The second session should write its final JSON to `session_output/cloud_skill_output.json`.
