---
name: project-bootstrap
description: Inspect project goals & the 3 Workforce Reference Docs, auto-create missing AGENTS.md/CLAUDE.md/QWEN.md/GEMINI.md or ask user to Keep/Update/Modify existing ones, and select needed skills.sh packages.
---
# Project Bootstrap & AI Skill Selection (`project-bootstrap`)

## When to Use
- When onboarding a new or existing project (current repo or `--workspace <path>`).

## Mandatory Steps
1. **Read Reference Docs:** Always check `1.Personal-Agent-Documents.md`, `2.The-Personal-AI-Workforce-Company.md`, and `3.Best-Practices-for-Managing-the-User-AI.md`.
2. **Detect Project Goals & Stack:** Inspect `README.md`, `requirements.txt`, `pyproject.toml`, `package.json`, `Dockerfile`, and database files.
3. **Check Agent Instruction Files (`AGENTS.md`, `CLAUDE.md`, `QWEN.md`/`QWENS.md`, `GEMINI.md`):**
   - If **missing**: Auto-create tailored to the project's goals and the 3 reference documents.
   - If **already exists**: NEVER overwrite silently — ask the user whether to **Keep (`k`)**, **Update/Append (`u`)**, or **Modify/Regenerate (`m`)**, then implement their choice.
4. **AI Skill Decision (`skills.sh`):** Recommend only the skills that match the project's stack & goals, and install with user confirmation.

## CLI Commands
```bash
# Current project bootstrap + AI skill recommendation
python3 main.py --bootstrap --install-skills

# External project (--workspace) bootstrap
python3 main.py --bootstrap --workspace /path/to/MyApp --goal "Your project goal"

# AI-driven skills.sh recommender script
bash scripts/install_recommended_skills.sh --workspace /path/to/MyApp --dry-run
```
