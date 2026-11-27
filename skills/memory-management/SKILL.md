---
name: memory-management
description: Read and save persistent workspace-scoped memory (JSON Long-Term + Vector Index) for both current project and --workspace targets.
---
# Persistent Memory Management (`memory-management`)

## Commands (Current Project)
- Recall recent or hybrid-search memory:
  `python3 main.py --memory-read "<query>"`
- Save CEO-approved decision/lesson:
  `python3 main.py --memory-write "<topic>" "<summary>" --tags tag1,tag2 --approve`

## Commands (External `--workspace` Zero-Pollution Mode)
- Recall workspace-specific memory:
  `python3 main.py --workspace /path/to/Project --memory-read "<query>"`
- Save workspace-specific memory (stored safely under `workspaces/<slug>/memory_store/`):
  `python3 main.py --workspace /path/to/Project --memory-write "<topic>" "<summary>" --approve`

## Safety Rule
- NEVER call `--memory-write --approve` without explicit CEO approval.
