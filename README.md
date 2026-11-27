# Personal AI Workforce Blueprint (v10 — Hardened Production-Grade)

4-Tier AI Workforce (`CEO → Assistant AI → Manager AI → Staff AI`) with:
- **Multi-Agent CLI Launcher (`Pattern B+` Zero-Pollution)** ([main.py](main.py) + [launcher.py](launcher.py)) for OpenCode / Claude / Qwen / Agy, with `--doctor` asset diagnostics and `--workspace <path>` isolation
- **Dynamic YAML Tiered LLM Client** ([llm/client.py](llm/client.py)): Anthropic Messages API, Gemini (`x-goog-api-key` header), Groq, OpenAI, Ollama, `httpx` + retry/backoff (429/5xx)
- **Persistent Workspace-Isolated Memory & Vector Store** ([harness/memory/vector_store.py](harness/memory/vector_store.py)): Hybrid keyword + cosine vector search (`--memory-read`, `--memory-write --approve`)
- **Project Bootstrap & AI Skill Decision Engine** ([harness/project_bootstrap.py](harness/project_bootstrap.py)): Syncs `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `GEMINI.md` and recommends/installs `skills.sh` packages via `npx -y skills@latest`
- **Hardened Docker Sandbox** (`--network=none`, `--read-only`, `--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec`, `--name` + `docker kill` on timeout)
- **AST Code Review** ([tools/code_review_tool.py](tools/code_review_tool.py)) + Bandit/Ruff/Mypy in CI
- **Full Async Quality Gate** (`ManagerAI.run_workflow_async`) with Planner, STM, Tracer & Circuit Breaker
- **Localhost/Token-Protected Observability Dashboard** ([api/dashboard.py](api/dashboard.py)) supporting multi-workspace traces, costs & memory inspection

## Quick Start
```bash
# 1. Environment setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Diagnostics, Demo & Tests
python3 main.py --doctor                         # Diagnose CLI asset wiring
python3 demo.py                                  # Offline 4-Tier Workflow Demo
python3 -m unittest discover -s tests -v         # Run All 16 Unit Tests

# 3. Interactive CLI Launcher & Pattern B+ Workspace Mode
python3 main.py                                  # Interactive CLI Launcher
python3 main.py --workspace ~/Projects/MyApp     # Zero-Pollution External Project Mode

# 4. Persistent Memory, Bootstrap & Skills
python3 main.py --memory-read ""                 # Read recent long-term memory
python3 main.py --memory-write "Topic" "Summary" --approve
python3 main.py --bootstrap --dry-run            # Check/sync agent instruction files
python3 main.py --recommend-skills --dry-run     # AI-recommended skills.sh packages

# 5. Production Workflow & Dashboard
python3 main.py --run "Fix the checkout bug."    # Run with real LLM + Docker sandbox
python3 api/dashboard.py                         # Dashboard (127.0.0.1:8080)
```

For full Burmese + Traditional Chinese usage documentation, see [usage_create_personal_agent_blueprint.md](usage_create_personal_agent_blueprint.md).
