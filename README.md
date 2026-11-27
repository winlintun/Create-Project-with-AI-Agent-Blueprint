# Personal AI Workforce Blueprint (v9 — Hardened Production-Grade)

4-Tier AI Workforce (`CEO → Assistant AI → Manager AI → Staff AI`) with:
- **Multi-Agent CLI Launcher** (`main.py` + `launcher.py`) for OpenCode / Claude / Qwen / Agy
- **Dynamic YAML Tiered LLM Client** (`llm/client.py`): Anthropic Messages API, Gemini (`x-goog-api-key` header), Groq, OpenAI, Ollama, `httpx` + retry/backoff (429/5xx)
- **Hardened Docker Sandbox** (`--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec`, `--name` + `docker kill` on timeout)
- **AST Code Review** (`tools/code_review_tool.py`) + Bandit in CI
- **Full Async Quality Gate** (`ManagerAI.run_workflow_async`) with Planner, STM, Tracer & Circuit Breaker
- **VectorMemory Protocol** (`harness/memory/vector_store.py`) + **Localhost/Token-Protected Observability Dashboard** (`api/dashboard.py`)

## Quick Start
```bash
cp .env.example .env
python3 main.py                                  # Interactive CLI Launcher
python3 demo.py                                  # Offline Workflow Demo
python3 -m unittest discover -s tests -v         # Run All Unit Tests
python3 api/dashboard.py                         # Dashboard (127.0.0.1:8080)
```
