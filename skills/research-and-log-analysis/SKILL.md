---
name: research-and-log-analysis
description: Investigate errors, inspect logs safely within allowed_root, and perform hybrid RAG / web research with evidence.
---
# Research & Log Analysis (`research-and-log-analysis`)

## Procedure
1. **Evidence First:** Inspect logs using path-contained `log_reader` (never read outside `allowed_root`).
2. **Local Knowledge:** Query local docs with `hybrid_rag` (keyword + cosine semantic similarity) and recall past incidents via `memory_read`.
3. **External Lookup:** Use `web_search` (Tavily / Brave / DuckDuckGo) when official docs or external error codes are needed.
4. **Output Format:** Return structured root-cause findings containing:
   - Exact file/log lines observed
   - Root cause hypothesis
   - Recommended minimal fix & risks
