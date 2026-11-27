# Personal AI Workforce Blueprint (v8) — အသုံးပြုပုံ လမ်းညွှန် (Usage README)

ဤ README သည် `create_personal_agent_blueprint.py` Generator Script နှင့် ၎င်းမှ ထုတ်ပေးသော **Personal AI Workforce (v8)** ပရောဂျက်ကို သင့် Linux Dev PC / Server တွင် စတင်တည်ဆောက်ခြင်း၊ ချိန်ညှိခြင်းနှင့် လက်တွေ့ Run ခြင်းတို့အတွက် အဆင့်ဆင့် လမ်းညွှန်ဖြစ်ပါသည်။

---

## 1. လိုအပ်ချက်များ (Prerequisites)

- **Python 3.11+** (Core script၊ CLI Launcher၊ Demo နှင့် Unit Tests အားလုံးသည် Python Standard Library သီးသန့်ဖြင့် ပြင်ပ package မလိုဘဲ Run နိုင်ပါသည်)
- **Optional Python Packages** (ပိုမိုလှပသော CLI Table၊ YAML loader၊ `httpx` HTTP client နှင့် Observability Web Dashboard အတွက်):
  ```bash
  pip install -r requirements.txt
  ```
- **Docker** (Production တွင် `docker_python_runner` ဖြင့် ဘေးကင်းစွာ Code Run ရန် — 沙盒隔離 / Sandbox Isolation)
- **AI CLI Tools** (မိမိသုံးလိုသော CLI တစ်ခုခု — `opencode`, `claude`, `qwen`, သို့မဟုတ် `agy`)

---

## 2. Generator Script (`create_personal_agent_blueprint.py`) အသုံးပြုပုံ

`create_personal_agent_blueprint.py` သည် Project Folder Structure (ဖိုင် ၁၀၇ ခု) ကို အလိုအလျောက် တည်ဆောက်ပေးပြီး ရှိပြီးသားဖိုင်များကို မတော်တဆ မဖျက်မိစေရန် **Safe-by-Default** (ပုံမှန်အားဖြင့် ရှိပြီးသားဖိုင်ကို Skip လုပ်ခြင်း) စနစ်ဖြင့် ရေးသားထားပါသည်။

| Command | လုပ်ဆောင်ချက် (What it does) |
| :--- | :--- |
| `python3 create_personal_agent_blueprint.py --self-test` | Temp directory ထဲတွင် ဖိုင် ၁၀၇ ခုလုံး စမ်းသပ်ထုတ်ပြီး `compileall` နှင့် Unit Test ၁၁ အုပ်စုလုံးကို အလိုအလျောက် စစ်ဆေးပေးသည်။ |
| `python3 create_personal_agent_blueprint.py --dry-run` | ဖိုင်အစစ် မရေးသေးဘဲ ဘယ်ဖိုင်တွေ Create / Skip ဖြစ်မလဲ ကြိုတင်စစ်ဆေးကြည့်သည်။ |
| `python3 create_personal_agent_blueprint.py` | လက်ရှိ folder အောက်တွင် `personal-ai-workforce/` project ကို တည်ဆောက်သည်။ |
| `python3 create_personal_agent_blueprint.py ~/Projects/my-ai-workforce` | မိမိစိတ်ကြိုက် folder လမ်းကြောင်းထဲတွင် တည်ဆောက်သည်။ |
| `python3 create_personal_agent_blueprint.py ./personal-ai-workforce --overwrite` | ရှိပြီးသားဖိုင်များကို အစားထိုး (Overwrite) ရေးသားသည်။ (`--force` ဟုလည်း သုံးနိုင်သည်) |

---

## 3. Environment နှင့် Model Tiers ပြင်ဆင်ခြင်း (Setup)

Project ဖန်တီးပြီးနောက် folder ထဲဝင်ပြီး `.env` ဖိုင်ကို ပြင်ဆင်ပါ (`main.py` နှင့် `launcher.py` တို့သည် `.env` ကို အလိုအလျောက် load လုပ်ပေးပါသည်)။

```bash
cd personal-ai-workforce
cp .env.example .env
```

`.env` ဖိုင်ထဲတွင် မိမိအသုံးပြုမည့် API Key များကို ဖြည့်ပါ (`.env` ကို `.gitignore` ထဲတွင် ထည့်ထားပြီးဖြစ်၍ Git ပေါ်သို့ မတော်တဆ မတက်နိုင်ပါ)-

```ini
# Agent CLI Launcher
DEFAULT_AGENT=opencode
AUTO_LAUNCH=false

# LLM Provider API Keys
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Execution Security
DOCKER_SANDBOX_IMAGE=python:3.12-slim
DOCKER_SANDBOX_RUNTIME=           # gVisor သုံးလိုပါက runsc ဟု ထည့်ပါ

# Observability Dashboard Auth (Optional Bearer Token)
WORKFORCE_DASHBOARD_TOKEN=
```

### Tiered Budget Model Routing (`config/model_tiers.yaml`)

`config/model_tiers.yaml` ကို ပြင်ဆင်ရုံဖြင့် Code ပြန်မပြင်ဘဲ Runtime တွင် Model များကို ပြောင်းလဲနိုင်သည် (分層預算模型 / Cost Optimization)-
- **Tier 1 (`assistant_ai`, `manager_ai`):** Complex reasoning & planning အတွက် Premium Models (`claude-sonnet-4-5`, `gemini-2.5-pro`)
- **Tier 2 (`researcher`, `coder`, `reviewer`, `writer_tutor`, `devops`, `security_auditor`):** Staff tasks များအတွက် Budget Models (`gemini-3.5-flash-lite`, Groq `llama-3.3-70b-versatile`, Local Ollama `qwen2.5:7b`)
- Primary Provider ကျသွားလျှင် **Fallback Chain (`備援鏈`)** အတိုင်း နောက်တစ်ခုသို့ အလိုအလျောက် ပြောင်းလဲပေးပြီး HTTP 429/5xx တွင် `Retry-After` backoff ဖြင့် ပြန်ကြိုးစားပေးသည်။

---

## 4. Multi-Agent CLI Launcher (`main.py`) အသုံးပြုပုံ

`main.py` ကို Run လိုက်သည်နှင့် Interactive Menu ပေါ်လာပြီး မိမိသုံးလိုသော CLI Agent ကို ရွေးချယ်နိုင်ပါသည်-

```bash
# 1. Interactive Menu ဖွင့်ရန် (1: OpenCode, 2: Claude, 3: Qwen, 4: Agy, 5: Demo, q: Quit)
python3 main.py

# 2. Menu မပြဘဲ CLI တစ်ခုကို တိုက်ရိုက် Launch လုပ်ရန်
python3 main.py --agent opencode
python3 main.py --agent claude
python3 main.py --agent qwen
python3 main.py --agent agy

# 3. CLI မဖွင့်သေးဘဲ Context Injection နှင့် Env Filtering ကို စမ်းသပ်ကြည့်ရန်
python3 main.py --agent opencode --dry-run
```

### CLI-Specific Context Injection နှင့် Env Security
Launcher သည် ရွေးလိုက်သော CLI အလိုက် Rule ဖိုင်များ (`AGENTS.md`, `CLAUDE.md`, `config/language_profile.yaml`, `config/model_tiers.yaml`) ကို အလိုအလျောက် Inject/Sync လုပ်ပေးပြီး မသက်ဆိုင်သော OS Secrets များကို စစ်ထုတ် (Filter) ပေးသည်-

| CLI Agent | Auto-Injected / Synced Context File |
| :--- | :--- |
| `opencode` | `opencode.json` (`instructions` list sync) |
| `claude` | `CLAUDE.md` |
| `qwen` | `.qwen_context.md` |
| `agy` | `.agy_context.md` |

---

## 5. Offline Demo Simulation (`demo.py`) စမ်းသပ်ခြင်း

ပြင်ပ API Key သို့မဟုတ် CLI မရှိသေးဘဲ 4-Tier Workforce (`CEO → Assistant Gatekeeper → Manager Planner/Circuit Breaker → Staff`) နှင့် Tier 1/Tier 2 Model Routing ကို စမ်းသပ်လိုပါက-

```bash
python3 demo.py
# သို့မဟုတ်
python3 main.py --demo
```

- `demo.py` သည် Production `docker_python_runner` နှင့် မရောထွေးစေရန် သီးသန့် `demo_python_runner` ကိုသာ အသုံးပြုထားပါသည်။
- `AssistantAI.draft_directive()` ခေါ်ချိန်တွင် Token နှင့် Cost မှတ်တမ်းကို `logs/cost_logs/<session_id>.jsonl` ထဲသို့ အလိုအလျောက် သိမ်းဆည်းပေးပါသည်။

---

## 6. Observability Web Dashboard (`api/dashboard.py`) ဖွင့်ကြည့်ခြင်း

Trace Logs (`logs/trace_logs/`) နှင့် Token Cost Summaries (`logs/cost_logs/`) များကို ကြည့်ရှုရန် (可觀察性 / Observability)-

```bash
# Default 127.0.0.1:8080 တွင်သာ Bind လုပ်၍ ဖွင့်သည်
python3 api/dashboard.py
# သို့မဟုတ်
uvicorn api.dashboard:app --host 127.0.0.1 --port 8080 --reload
```

| Endpoint | ဖော်ပြချက် |
| :--- | :--- |
| `GET /dashboard` | Dashboard ပင်မစာမျက်နှာ |
| `GET /api/traces?session_id=<id>` | Session တစ်ခုချင်းစီ၏ Trace spans များ |
| `GET /api/costs?session_id=<id>` | Session တစ်ခုချင်းစီ၏ LLM call cost မှတ်တမ်းများ |
| `GET /api/costs/summary?session_id=<id>` | စုစုပေါင်း Input/Output Tokens နှင့် Estimated Cost (USD) |

`.env` တွင် `WORKFORCE_DASHBOARD_TOKEN` သတ်မှတ်ထားပါက Request Header တွင် `Authorization: Bearer <your-token>` ထည့်ပေးရပါမည်။

---

## 7. စစ်ဆေးခြင်း နှင့် CI Checks (Testing & Quality)

```bash
# 1. Unit Tests ၁၁ အုပ်စုလုံး Run ရန် (Zero external dependencies)
python3 -m unittest discover -s tests -v

# 2. Docker Sandbox Isolation စမ်းသပ်ရန် (Docker ရှိသောစက်တွင်)
bash tests/integration/docker_sandbox_test.sh

# 3. Code Quality & Security Scans (ruff, mypy, bandit သွင်းထားလျှင်)
ruff check .
mypy agents/ api/ harness/ llm/ tools/ launcher.py demo.py main.py
bandit -r agents/ api/ harness/ llm/ tools/ launcher.py
```

---

## 8. Community Skills ထပ်ထည့်ခြင်း (`skills.sh`)

Project ထဲတွင် `skills.sh` စံနှုန်းကိုက် built-in skill ၈ ခု (`create-prd`, `phase-prd`, `language-communication`, `prompt-refinement`, `dynamic-planning`, `quality-gate-review`, `research-and-log-analysis`, `bilingual-cs-tutoring`) ပါဝင်ပြီး ဖြစ်ပါသည်။ Community skills များ ထပ်ထည့်လိုပါက Node.js (`npx`) ရှိသော Dev PC တွင် အောက်ပါအတိုင်း ကြိုတင်စစ်ဆေးပြီး သွင်းနိုင်ပါသည်-

```bash
# ဘယ် skills တွေ သွင်းမလဲ ကြိုကြည့်ရန်
bash scripts/install_recommended_skills.sh --dry-run

# အတည်ပြုပြီး သွင်းရန် (Pinned CLI version + confirmation prompt ပါဝင်သည်)
bash scripts/install_recommended_skills.sh
```

---

## 9. လုံခြုံရေး သတိပြုရန်အချက်များ (Security Notes)

- **Gatekeeper & Tamper Check:** CEO Approve ပြီးနောက် Directive သို့မဟုတ် Constraints ပြောင်းလဲသွားပါက SHA-256 Digest ဖြင့် အလိုအလျောက် ဖမ်းမိပြီး Approval ပျက်ပြယ်ပါသည်။
- **Docker Sandbox:** Production တွင် `CoderAgent` သည် `docker_python_runner` (`--network=none`, `--read-only`, `--cap-drop=ALL`, `--tmpfs`, timeout ကျလျှင် `docker kill`) ကိုသာ အသုံးပြုပါသည်။
- **AST Code Review:** `tools/code_review_tool.py` သည် `eval`, `exec`, `__import__`, `getattr`, `open(..., 'w')`, `builtins.open`, `io.open`, dangerous dunders (`__subclasses__`, `__globals__`) နှင့် SQL/Shell အန္တရာယ်ရှိ command များကို စစ်ဆေးပေးပါသည်။
- **Audit Log Privacy:** `logs/action_logs/` နှင့် `logs/decision_logs/` တို့သည် `api_key`, `token`, `password`, `Bearer ...` စသည်တို့ကို `***REDACTED***` အဖြစ် အလိုအလျောက် ဖုံးကွယ်ပြီး `chmod 0600` ဖြင့် သိမ်းဆည်းပါသည်။
