---
name: prompt-refinement
description: Refine raw CEO requests into tamper-evident StructuredContextPayload directives with clear constraints and HITL approval.
---
# Prompt Refinement (`prompt-refinement`)

## Procedure
1. Read raw CEO intent and recall relevant prior episodes via `memory_read`.
2. Rewrite vague goals into a specific, verifiable `approved_directive`.
3. Attach mandatory safety constraints (e.g., no production schema changes, no protected data edits).
4. Present Intent, Directive, and Constraints to the CEO for explicit approval (`y` / `n` / `e`).
5. Never forward an unapproved or tampered payload to `ManagerAI`.
