# Personal AI Workforce Blueprint (v10) — အသုံးပြုပုံ လမ်းညွှန် (Usage README)

ဤ README သည် `create_personal_agent_blueprint-v10.py` Generator Script နှင့် ၎င်းမှ ထုတ်ပေးသော **Personal AI Workforce (v10 — Pattern B+ Native CLI Assets & Zero-Pollution Workspace Mode)** ကို စတင်တည်ဆောက်ခြင်း၊ ရှိပြီးသား ပရောဂျက်များ (`IncomeTrackerv1`, `Novel-v1` စသည်) နှင့် Data/Code မထိခိုက်ဘဲ ချိတ်ဆက် Run ခြင်းတို့အတွက် အဆင့်ဆင့် လမ်းညွှန်ဖြစ်ပါသည်။

---

## 1. လိုအပ်ချက်များ (Prerequisites)

- **Python 3.11+** (CLI Launcher, Demo နှင့် Unit Tests **၁၆ အုပ်စု**လုံးသည် Python Standard Library သီးသန့်ဖြင့် Run နိုင်ပါသည်)
- **Virtual Environment (`.venv`) နှင့် Python Packages** (Rich CLI Table, PyYAML, `httpx`, FastAPI/Uvicorn Dashboard အတွက်):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **Docker** (Production တွင် `docker_python_runner` ဖြင့် ဘေးကင်းစွာ Code Run ရန် — 沙盒隔離 / Sandbox Isolation)
- **AI CLI Tools** (`opencode`, `claude`, `qwen`, သို့မဟုတ် `agy`)

---

## 2. Generator Script (`create_personal_agent_blueprint-v10.py`) အသုံးပြုပုံ

`create_personal_agent_blueprint-v10.py` သည် Project Structure (**ဖိုင် ၁၁၈ ခု**) ကို အလိုအလျောက် တည်ဆောက်ပေးပြီး ရှိပြီးသားဖိုင်များကို မတော်တဆ မဖျက်မိစေရန် ပုံမှန်အားဖြင့် **Skip (Safe-by-Default)** လုပ်ပေးပါသည်။

| Command | လုပ်ဆောင်ချက် (What it does) |
| :--- | :--- |
| `python3 create_personal_agent_blueprint-v10.py --self-test` | Temp directory ထဲတွင် ဖိုင် ၁၁၈ ခု စမ်းသပ်ထုတ်ပြီး `compileall` နှင့် Unit Test ၁၆ အုပ်စုလုံးကို အလိုအလျောက် စစ်ဆေးပေးသည်။ |
| `python3 create_personal_agent_blueprint-v10.py --dry-run` | ဖိုင်အစစ် မရေးသေးဘဲ Create / Skip ဖြစ်မည့် ဖိုင်စာရင်းကို ကြိုကြည့်သည်။ |
| `python3 create_personal_agent_blueprint-v10.py` | လက်ရှိ folder အောက်တွင် `personal-ai-workforce/` ကို တည်ဆောက်သည်။ |
| `python3 create_personal_agent_blueprint-v10.py ~/Projects/personal-ai-workforce` | မိမိစိတ်ကြိုက် လမ်းကြောင်းထဲတွင် တည်ဆောက်သည်။ |
| `python3 create_personal_agent_blueprint-v10.py ~/Projects/personal-ai-workforce --overwrite` | ရှိပြီးသားဖိုင်များကို အစားထိုး (Overwrite) ရေးသားသည်။ (`--force` ဟုလည်း သုံးနိုင်သည်) |

---

## 3. Environment နှင့် Config များ ပြင်ဆင်ခြင်း (Setup)

```bash
cd ~/Projects/personal-ai-workforce
cp .env.example .env
```

`main.py` နှင့် `launcher.py` တို့သည် `.env` ဖိုင်ကို အလိုအလျောက် load လုပ်ပေးပြီး `.env` ကို `.gitignore` ထဲတွင် ထည့်ထားပြီးဖြစ်ပါသည်။

### အဓိက Config ဖိုင် ၃ ခု (Runtime Dynamic Load)
- **`config/model_tiers.yaml`** (分層預算模型 / Tiered Budget Routing):
  - **Tier 1 (`assistant_ai`, `manager_ai`):** Premium Reasoning Models (`claude-sonnet-4-5`, `gemini-2.5-pro`)
  - **Tier 2 (`researcher`, `coder`, `reviewer`, `writer_tutor`, `devops`, `security_auditor`):** Budget Models (`gemini-2.5-flash-lite`, Groq `llama-3.3-70b-versatile`, Local Ollama `qwen2.5:7b`)
  - Anthropic (`x-api-key`) နှင့် Gemini (`x-goog-api-key` header) တို့ကို Fallback Chain (`備援鏈`) နှင့် HTTP 429/5xx `Retry-After` backoff ဖြင့် ချိတ်ဆက်ထားသည်။
- **`config/safety_policy.yaml`** (Protected Data Paths):
  - `data/**`, `backups/**`, `migrations/**`, `*.db`, `*.sqlite*`, `*.sql`, `.env`, `.env.*` တို့ကို recursive `**` glob ဖြင့် runtime တွင် အလိုအလျောက် ကာကွယ်ပေးသည်။
- **`config/language_profile.yaml`**:
  - မြန်မာစာ (Primary) + Traditional Chinese (`繁體中文`, TOCFL B1) + Basic English စည်းမျဉ်းများ။

---

## 4. Pattern B: ရှိပြီးသား ပရောဂျက်များနှင့် Zero-Pollution ချိတ်ဆက်သုံးပုံ (`--workspace`)

`personal-ai-workforce/` ကို တစ်နေရာတည်းတွင် ထားရှိပြီး မည်သည့် ရှိပြီးသား ပရောဂျက် (`IncomeTrackerv1`, `Novel-v1` စသည်) ကိုမဆို **ဖိုင်တစ်ဖိုင်မှ မထည့်ဘဲ / မဖျက်ဘဲ (Zero-Pollution)** ချိတ်ဆက် Run နိုင်ပါသည်-

```bash
# 1. Interactive Menu ဖွင့်ပြီး ရှိပြီးသား Project ကို ချိတ် Run ရန်
python3 main.py --workspace ~/Projects/IncomeTrackerv1

# 2. CLI တစ်ခုကို တိုက်ရိုက် ချိတ် Run ရန်
python3 main.py --workspace ~/Projects/IncomeTrackerv1 --agent opencode
python3 main.py --workspace ~/Projects/Novel-v1 --agent claude
python3 main.py --workspace ~/Projects/Novel-v1 --agent qwen
python3 main.py --workspace ~/Projects/Novel-v1 --agent agy

# 3. Git Branch အသစ်ခွဲပြီး ဘေးကင်းစွာ Run ရန် (Recommended)
python3 main.py --workspace ~/Projects/IncomeTrackerv1 --agent opencode --create-branch ai-workforce/fix-bug

# 4. CLI မဖွင့်သေးဘဲ Context Injection, Env Filtering နှင့် Git Guard ကို ကြိုစစ်ရန်
python3 main.py --workspace ~/Projects/IncomeTrackerv1 --agent opencode --dry-run
```

### Zero-Pollution နှင့် Git Guard အလုပ်လုပ်ပုံ
- **Target Project ထဲ ဖိုင် `0` ခုသာ ဝင်သည်:** Runtime context နှင့် `.workforce_runtime.json` အားလုံးကို `personal-ai-workforce/workspaces/<project_name>/` ထဲတွင်သာ သီးသန့်သိမ်းဆည်းသည်။
- **Existing Rules Read-Only Merge:** Target project ထဲတွင် ကိုယ်ပိုင် `AGENTS.md` သို့မဟုတ် `CLAUDE.md` ရှိနေလျှင် Overwrite မလုပ်ဘဲ Read-only ဖတ်ယူ၍ Workforce rules နှင့် ပေါင်းစပ်ပေးသည်။
- **Git Pre-Flight Guard:** Target project တွင် uncommitted changes ရှိနေလျှင် သို့မဟုတ် `main`/`master` branch ပေါ်ရောက်နေလျှင် CLI မဖွင့်မီ သတိပေးချက် ပြပေးသည်။
- **CLI-Specific Injection:** `opencode` သည် `OPENCODE_CONFIG` မှတဆင့် `workspaces/<slug>/opencode.json` ကို တိုက်ရိုက်ဖတ်ပြီး `claude`, `qwen`, `agy` တို့အတွက် `workspaces/<slug>/.<cli>_context.md` ဖန်တီးပေးသည်။

---

## 5. Offline Demo Simulation (`demo.py`) စမ်းသပ်ခြင်း

ပြင်ပ API Key သို့မဟုတ် CLI မရှိသေးဘဲ 4-Tier Workforce (`CEO → Assistant → Manager → Staff`) နှင့် Tier 1/Tier 2 Model Routing ကို စမ်းသပ်ရန်-

```bash
python3 demo.py
# သို့မဟုတ်
python3 main.py --demo
```

- `demo.py` သည် Production `docker_python_runner` နှင့် မရောထွေးစေရန် သီးသန့် `demo_python_runner` ကိုသာ သုံးထားသည်။
- `AssistantAI.draft_directive()` ခေါ်ချိန်တွင် Token & Cost log ကို `logs/cost_logs/<session_id>.jsonl` ထဲသို့ အလိုအလျောက် သိမ်းပေးသည်။

---

## 6. Observability Web Dashboard (`api/dashboard.py`) ဖွင့်ကြည့်ခြင်း

```bash
# တိုက်ရိုက် Run နိုင်သည် (Default 127.0.0.1:8080 တွင်သာ Bind လုပ်သည်)
python3 api/dashboard.py
# သို့မဟုတ်
uvicorn api.dashboard:app --host 127.0.0.1 --port 8080 --reload
```

| Endpoint | ဖော်ပြချက် |
| :--- | :--- |
| `GET /dashboard` | Dashboard ပင်မစာမျက်နှာ |
| `GET /api/sessions?workspace=<slug>` | Workspace အလိုက် Session စာရင်းများ |
| `GET /api/memory?workspace=<slug>&q=<query>` | Persistent Long-Term & Vector Memory ရှာဖွေခြင်း |
| `GET /api/traces?session_id=<id>&workspace=<slug>` | Session အလိုက် Trace spans များ |
| `GET /api/costs?session_id=<id>&workspace=<slug>` | Session အလိုက် LLM call cost မှတ်တမ်းများ |
| `GET /api/costs/summary?session_id=<id>&workspace=<slug>` | စုစုပေါင်း Input/Output Tokens နှင့် Estimated Cost (USD) |

`.env` တွင် `WORKFORCE_DASHBOARD_TOKEN` ထည့်ထားပါက Request Header တွင် `Authorization: Bearer <token>` ထည့်ပေးရပါမည်။

---

## 7. v10 CLI အသစ်များ (`--doctor`, Memory, `--run`, `--bootstrap`, `--recommend-skills`)

```bash
# 1. CLI Asset Wiring & Native Skills စစ်ဆေးရန် (Pattern B+)
python3 main.py --doctor

# 2. Persistent Memory ဖတ်ရန် / CEO Approval ဖြင့် သိမ်းရန် (JSON + Vector Store)
python3 main.py --memory-read ""
python3 main.py --memory-read "Stripe timeout"
python3 main.py --memory-write "Stripe Retry" "Added exponential backoff" --tags "stripe,api" --approve

# 3. Production 4-Tier Workflow (Real LLM + Docker Sandbox)
python3 main.py --run "Fix the checkout bug."

# 4. Project Bootstrap (AGENTS.md, CLAUDE.md, QWEN.md, GEMINI.md Sync)
python3 main.py --bootstrap --dry-run

# 5. AI Skill Decision Engine (skills.sh via npx -y skills@latest)
python3 main.py --recommend-skills --dry-run
python3 main.py --recommend-skills --yes
```

---

## 8. စစ်ဆေးခြင်း နှင့် CI Checks (Testing & Quality)

```bash
# 1. Unit Tests ၁၆ အုပ်စုလုံး Run ရန် (Zero external dependencies)
.venv/bin/python -m unittest discover -s tests -v

# 2. Docker Sandbox Isolation စမ်းသပ်ရန်
bash tests/integration/docker_sandbox_test.sh

# 3. Code Quality & Security Scans (Ruff UP035/E501 & Mypy clean)
ruff check .
mypy agents/ api/ harness/ llm/ tools/ launcher.py demo.py main.py
bandit -r agents/ api/ harness/ llm/ tools/ launcher.py
```

---

## 9. Community Skills ထပ်ထည့်ခြင်း (`skills.sh`)

```bash
bash scripts/install_recommended_skills.sh --dry-run
bash scripts/install_recommended_skills.sh
```

---

## 10. လုံခြုံရေး အနှစ်ချုပ် (Security Highlights)

- **Gatekeeper & SHA-256 Tamper Check:** CEO Approve ပြီးနောက် Directive/Constraints ပြောင်းသွားပါက Approval အလိုအလျောက် ပျက်ပြယ်သည်။
- **Docker Hardening:** `--network=none`, `--read-only`, `--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec,nosuid,nodev`, `--pids-limit=64`, optional `--cap-add` allowlist နှင့် timeout ကျလျှင် `docker kill` လုပ်ပေးသည်။
- **AST Code Review:** `eval`, `exec`, `__import__`, `getattr`, `open`/`builtins.open`/`io.open` write mode, `Path.write_text`/`write_bytes`, dangerous dunders (`__subclasses__`, `__globals__`) နှင့် SQL/Shell အန္တရာယ်များကို စစ်ဆေးပေးသည်။
- **Thread-Safe Memory & Redacted Logs:** `AutoConsolidator` တွင် `threading.Lock()` နှင့် CEO-approval gate ပါဝင်ပြီး Audit Logs များသည် API keys/tokens များကို `***REDACTED***` ဖုံးကွယ်ကာ `chmod 0600` ဖြင့် သိမ်းဆည်းသည်။

---

## 11. CI Quality Rules — နောက်ထပ် မပြုလုပ်ရန် သတိပေးချက်များ

Blueprint v10 မှ generate လုပ်သည့် project အားလုံးသည် CI (ruff → mypy → bandit → unittest → docker) အဆင့် ၅ ဆင့်လုံး တန်းအတွက် အစိမ်းရောင် ဖြစ်ရန် အောက်ပါ စည်းမျဉ်းများကို template ထဲမှာ ကြိုပြီး ကာကွယ်ထားပြီးဖြစ်သည် —

1. **`# type: ignore` comment မထည့်ရ:** `pyproject.toml` တွင် `ignore_missing_imports = true` ရှိသဖြင့် missing import များ အလိုအလျောက် ဖြေရှင်းပြီးဖြစ်သည်။ ထည့်ပါက `warn_unused_ignores = true` က mypy error ပြန်ထုတ်သည်။
2. **`list` များကို ကြို annotate လုပ်ရန်:** `sort()` မတိုင်မီ `scored: list[dict[str, Any]] = []` ကြိုရေးပြီး sort key တွင် `float(x["score"])` သုံးရန် — မဟုတ်ပါက mypy `arg-type` error ထုတ်သည်။
3. **bandit `# nosec` format:** code များကြားတွင် **comma + space** လိုအပ်သည် (`# nosec B603, B607`) — `B603,B607` (space မပါ) ဆိုပါက နောက်ဆုံး code တစ်ခုပဲ အသက်ဝင်သည်။ furthermore comment ကို call စတင်သည့် အတူတူ line မှာပဲ ရေးရန် (အပေါ်ကြောင်းမှာ ရေးလျှင် အလုပ်မလုပ်)။
4. **Import sort (ruff I001):** `from collections.abc import ...` ကို `from contextlib/dataclasses/pathlib` များမတိုင်မီ ရေးရန်၊ `datetime.UTC` (not `timezone.utc`), `OSError` (not `EnvironmentError`) သုံးရန်၊ `dict.values()` ကို values ချည်းပဲ သုံးသည့်နေရာမှာ သုံးရန်။
5. **Shebang ပါသည့် ဖိုင် (`demo.py`, `main.py`, `*.sh`):** blueprint က `chmod 0o755` အလိုအလျောက် လုပ်ပေးသည် (ruff EXE001 ကို ကာကွယ်)။
