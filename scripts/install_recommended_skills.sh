#!/usr/bin/env bash
set -euo pipefail
SKILLS_CLI_VERSION="${SKILLS_CLI_VERSION:-1.0.0}"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
SKILLS=(
  "vercel-labs/skills|find-skills|Skill discovery helper"
  "addyosmani/agent-skills|planning-and-task-breakdown|Manager AI planning helper"
  "addyosmani/agent-skills|code-review-and-quality|Reviewer Agent quality checklist"
  "mattpocock/skills|research|Researcher Agent workflow"
)
echo "=== Recommended skills.sh Packages (CLI: skills@${SKILLS_CLI_VERSION}) ==="
for entry in "${SKILLS[@]}"; do
  IFS="|" read -r repo skill purpose <<< "$entry"
  echo "  - ${repo} --skill ${skill} (${purpose})"
done
[[ "$DRY_RUN" == "true" ]] && { echo "[DRY-RUN] No packages installed."; exit 0; }
read -r -p "Install via npx skills@${SKILLS_CLI_VERSION}? [y/N]: " c
[[ "$c" =~ ^[Yy]$ ]] || exit 0
for entry in "${SKILLS[@]}"; do
  IFS="|" read -r repo skill _ <<< "$entry"
  npx "skills@${SKILLS_CLI_VERSION}" add "${repo}" --skill "${skill}"
done
