#!/usr/bin/env bash
set -euo pipefail

# AI-Driven skills.sh Skill Recommender & Installer
# Analyzes the current project (or --workspace <path>) + 3 Workforce Reference Docs,
# decides which skills.sh packages are needed, and installs them with user confirmation.
#
# Usage:
#   bash scripts/install_recommended_skills.sh --dry-run
#   bash scripts/install_recommended_skills.sh --workspace /path/to/MyApp --goal "FastAPI app"
#   bash scripts/install_recommended_skills.sh --yes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFORCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

exec python3 "${WORKFORCE_ROOT}/main.py" --recommend-skills "$@"
