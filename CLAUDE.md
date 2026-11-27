# Project Context & Agent Instructions (Personal AI Workforce v10)

## 1. User Language & Communication Profile (Mandatory)
- **Primary Language:** Burmese (မြန်မာစာ) — ရိုးရှင်းနားလည်လွယ်အောင် ရှင်းပြရမည်။
- **Academic / CS Terms:** Traditional Chinese (`繁體中文`, TOCFL B1) တွဲဖော်ပြရမည် (ဥပမာ — Derivative `導數`, Matrix `矩陣`, Integration `積分`, Algorithm `演算法`, Vector Database `向量資料庫`)။
- **English Level:** Basic — Coding/Tech keyword များကို မြန်မာလို အမြဲတွဲရှင်းပြရမည်။

## 2. Tech Stack & Storage Architecture
- **Languages & Frameworks:** Python 3.11+, FastAPI, Docker, httpx, Bash
- **Memory & RAG:** JSON Long-Term Memory + `InMemoryCosineVectorStore` by default; optional PostgreSQL + `pgvector` interface defined in `harness/memory/vector_store.py` (`VectorMemoryBackend`).
- **CLI Agents Supported:** OpenCode (`opencode`), Claude (`claude`), Qwen (`qwen`), Antigravity (`agy`)
- **PRD Workflow:** `docs/PRDs/active/` & `docs/PRDs/active/phases/` using `skills/create-prd/feature-template.md`
- **Testing:** `python3 -m unittest discover -s tests -v`

## 3. Hard Safety Rules
- **Gatekeeper & Tamper Check:** CEO Approval မပါဘဲ သို့မဟုတ် Approve ပြီးနောက် Directive ပြောင်းသွားပါက Manager AI မလုပ်ဆောင်ရ။
- **Execution Isolation:** Production code execution တွင် `docker_python_runner` (`--network=none --read-only --cap-drop=ALL --pids-limit=64`) ကိုသာ သုံးပါ။
- **Path Containment & Secret Redaction:** File tools များသည် `allowed_root` အတွင်းသာ ဖတ်ရမည်။ Audit log များတွင် Secret များကို Redact လုပ်ရမည်။

## 4. Sub-Agent Model Policy (Mandatory — 分層預算模型)
- **Tier 1 (Assistant AI, Manager AI):** Premium reasoning model (configured in `config/model_tiers.yaml`).
- **Tier 2 (Staff Agents):** Budget high-speed model (configured in `config/model_tiers.yaml`).

<!-- WORKFORCE-MANAGED-START -->
# personal-ai-workforce — Agent Instructions (CLAUDE)

> Auto-generated from project goals and Workforce Reference Docs (`1.Personal-Agent-Documents.md, 2.The-Personal-AI-Workforce-Company.md, 3.Best-Practices-for-Managing-the-User-AI.md`).

## 1. Project Goal & Scope (Ref Doc 1 — Project Charter)
- **Project:** `personal-ai-workforce`
- **Goal:** Personal AI Workforce Blueprint (v10 — Hardened Production-Grade) — 4-Tier AI Workforce (`CEO → Assistant AI → Manager AI → Staff AI`) with:
- **Detected Stack:** python, fastapi
- **Lifecycle:** `Start → Plan → Do & Test → Monitor → Close`

## 2. User Language & Communication Profile (Mandatory)
- **Primary Language:** Burmese (မြန်မာစာ) — ရိုးရှင်းနားလည်လွယ်အောင် ရှင်းပြရမည်။
- **Academic / CS Terms:** Pair with Traditional Chinese (`繁體中文`, TOCFL B1), e.g. Algorithm (`演算法`), Matrix (`矩陣`), Vector Database (`向量資料庫`).
- **English Level:** Basic — Coding/Tech keywords များကို မြန်မာလို အမြဲတွဲရှင်းပြရမည်။

## 3. 4-Tier AI Workforce Hierarchy & Harness Rules (Ref Doc 2 & 3)
- **Gatekeeper:** Never execute major changes without CEO approval; invalidate on directive tamper.
- **Circuit Breaker:** Max 2 retries per step with corrective feedback; escalate to CEO if still blocked.
- **Protected Data Guard:** NEVER delete, truncate, or overwrite `data/**`, `backups/**`, `migrations/**`, `*.db`, `*.sqlite*`, `*.sql`, `.env*`.
- **Persistent Memory CLI:**
  - Read: `python3 main.py --memory-read "<query>"`
  - Save (CEO approved): `python3 main.py --memory-write "<topic>" "<summary>" --approve`
<!-- WORKFORCE-MANAGED-END -->
