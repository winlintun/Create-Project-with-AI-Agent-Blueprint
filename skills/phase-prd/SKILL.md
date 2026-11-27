---
name: phase-prd
description: Break a large PRD into sequential, independently verifiable implementation phases in docs/PRDs/active/phases/.
---
# Phase PRD (`phase-prd`)

## When to Use
- When a feature PRD spans more than 3 modules or requires staged rollout.

## Procedure
1. Read the parent PRD from `docs/PRDs/active/<feature>.md`.
2. Split work into 2–5 small phases where each phase leaves tests passing.
3. Write phase plans under `docs/PRDs/active/phases/<feature>-phase-<N>.md`.
4. For each phase define: inputs, files touched, rollback plan, and exact verification test command.
5. Never start Phase N+1 until Phase N passes quality gate & security review.
