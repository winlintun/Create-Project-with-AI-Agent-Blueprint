---
name: create-prd
description: Generate a structured Product Requirements Document (PRD) in docs/PRDs/active/ using feature-template.md.
---
# Create PRD (`create-prd`)

## When to Use
- Before implementing any new feature, major refactor, or multi-step module.

## Procedure
1. Read `skills/create-prd/feature-template.md` as the mandatory structural blueprint.
2. Clarify scope, constraints, and non-goals with the CEO (User) before drafting.
3. Save the completed PRD to `docs/PRDs/active/<feature-slug>.md`.
4. Include:
   - Problem statement & user value
   - Functional & non-functional requirements
   - Security / Zero-Pollution constraints (`config/safety_policy.yaml`)
   - Acceptance criteria & verification commands
5. Request explicit CEO approval before handing off to `ManagerAI` or `Coder`.
