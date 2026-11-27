# personal-ai-workforce — Agent Instructions (QWEN)

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
