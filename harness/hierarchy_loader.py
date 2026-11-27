"""Runtime Hierarchy Policy Loader (`harness/hierarchy_loader.py`).

Loads `config/hierarchy_config.yaml` (PyYAML or stdlib fallback) so `ManagerAI`
respects `max_retries_per_step`, `max_concurrent_staff`, and CEO approval gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass(frozen=True)
class HierarchySettings:
    max_retries_per_step: int = 2
    max_concurrent_staff: int = 4
    require_ceo_approval_for_memory_write: bool = True
    auto_forward_allowed: bool = False


def load_hierarchy_config(config_path: Path | None = None) -> HierarchySettings:
    if config_path is None or not config_path.is_file():
        return HierarchySettings()
    raw = config_path.read_text(encoding="utf-8")
    if HAS_YAML:
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            return HierarchySettings()
        hier = data.get("hierarchy", {})
        if not isinstance(hier, dict):
            return HierarchySettings()
        t2 = hier.get("tier_2_assistant_ai", {}) or {}
        t3 = hier.get("tier_3_manager_ai", {}) or {}
        cb = t3.get("circuit_breaker", {}) or {}
        return HierarchySettings(
            max_retries_per_step=int(cb.get("max_retries_per_step", 2)),
            max_concurrent_staff=int(t3.get("max_concurrent_staff", 4)),
            require_ceo_approval_for_memory_write=bool(
                t3.get("require_ceo_approval_for_memory_write", True)
            ),
            auto_forward_allowed=bool(t2.get("auto_forward_allowed", False)),
        )

    retries = 2
    conc = 4
    req_mem = True
    auto_fwd = False
    for line in raw.splitlines():
        clean = line.split("#", 1)[0].strip()
        if clean.startswith("max_retries_per_step:"):
            retries = int(clean.split(":", 1)[1].strip())
        elif clean.startswith("max_concurrent_staff:"):
            conc = int(clean.split(":", 1)[1].strip())
        elif clean.startswith("require_ceo_approval_for_memory_write:"):
            req_mem = clean.split(":", 1)[1].strip().lower() == "true"
        elif clean.startswith("auto_forward_allowed:"):
            auto_fwd = clean.split(":", 1)[1].strip().lower() == "true"
    return HierarchySettings(
        max_retries_per_step=retries,
        max_concurrent_staff=conc,
        require_ceo_approval_for_memory_write=req_mem,
        auto_forward_allowed=auto_fwd,
    )
