"""Zero-dependency `.env` file loader (does not overwrite existing OS env vars)."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(env_path: Path, *, override: bool = False) -> int:
    if not env_path.exists() or not env_path.is_file():
        return 0
    loaded = 0
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        if key and (override or key not in os.environ):
            os.environ[key] = val
            loaded += 1
    return loaded
