---
name: dynamic-planning
description: Maintain a live, gated execution plan with Circuit Breaker (max 2 retries per step) and CEO escalation.
---
# Dynamic Planning (`dynamic-planning`)

## Core Rules
- Every multi-step task MUST start with a clear ordered checklist (Step 1..N) with an assigned owner (`researcher`, `coder`, `reviewer`, `security_auditor`, `devops`, `writer_tutor`).
- Update step status immediately: `pending` -> `in_progress` -> `completed` or `failed`.
- **Circuit Breaker (`斷路器`):** Maximum **2 retries** per step. Include concrete failure feedback on each retry.
- **Escalation:** If a step still fails after retries, STOP downstream steps immediately and escalate to the CEO with evidence and options.
- Always recall prior workspace memory before planning and consolidate CEO-approved results upon completion.
