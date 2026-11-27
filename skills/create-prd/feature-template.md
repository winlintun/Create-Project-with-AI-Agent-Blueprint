# PRD: {Feature Name}

- **PRD ID:** {PRD_ID}
- **Status:** Draft | CEO-Approved | In Progress | Completed
- **Owner:** Manager AI (Tier 1) & Staff Agents (Tier 2)

## 1. User Goal & Acceptance Criteria (`目標與驗收標準`)
- **Goal:** {Describe the exact end-to-end outcome the user needs}
- **Acceptance Criteria:**
  - [ ] {Concrete, verifiable user-facing requirement 1}
  - [ ] {Concrete, verifiable user-facing requirement 2}

## 2. Scope, Architecture & Safety Constraints (`範圍與安全限制`)
- **Files / Modules Affected:** `{list paths}`
- **Protected Data Guard:** Never modify or delete `data/**`, `backups/**`, `migrations/**`, `*.db`, `*.sqlite*`, `*.sql`, `.env*`.
- **Gatekeeper Approval:** Required before executing major changes or writing persistent memory.

## 3. Implementation Phases (`實作階段`)
### Phase 1: Foundation & Core Logic
- [ ] {task 1}
- [ ] {task 2}

### Phase 2: Integration & Edge Cases
- [ ] {task 3}

## 4. Mandatory Automated Testing Plan (`強制自動化測試計畫`)
- [ ] Unit tests covering core logic & edge cases (`python3 -m unittest discover -s tests -v`)
- [ ] Integration / smoke test verifying the feature works end-to-end
- [ ] Code quality & security checks (`ruff check .`, `mypy`, `bandit`)

## 5. Definition of Done (`完成定義`)
- [ ] All acceptance criteria implemented end-to-end (no `TODO` stubs left behind)
- [ ] All automated tests pass 100% with verifiable output
- [ ] Docs, configs, and agent instruction files updated cleanly
