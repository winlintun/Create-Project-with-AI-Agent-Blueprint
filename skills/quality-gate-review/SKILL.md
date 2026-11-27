---
name: quality-gate-review
description: Perform AST security checks, diff audits, protected-path verification, and test validation before completion.
---
# Quality Gate Review (`quality-gate-review`)

## Checklist (Mandatory Before Done)
1. **Security & AST Audit:** Block `eval`, `exec`, `compile`, `__import__`, unsafe `subprocess`, arbitrary file writes, and destructive SQL/shell (`DROP TABLE`, `rm -rf`).
2. **Path Containment & Zero-Pollution:** Verify no edits touch protected patterns in `config/safety_policy.yaml` (`data/**`, `backups/**`, `migrations/**`, `*.db`, `.env*`).
3. **Secret Redaction:** Confirm no API keys, tokens, or credentials appear in code, diffs, or logs.
4. **Minimal Diff:** Ensure changes stay focused on the approved directive without unintended regressions.
5. **Verification:** Run `python3 -m unittest discover -s tests -v` (or project test suite) and confirm 100% pass.
