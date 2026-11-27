"""
Hardened Docker Sandbox Runner (`tools/docker_python_runner_tool.py`)
- Adds `--name`, `--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec,nosuid,nodev`.
- On timeout, explicitly runs `docker kill <container_name>` so no orphan container survives.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 — runs fixed docker CLI argv only
import uuid
from typing import Any

ALLOWED_DOCKER_CAPS = frozenset({"NET_BIND_SERVICE"})


def build_docker_sandbox_cmd(
    python_code: str,
    *,
    container_name: str | None = None,
    image: str = "python:3.12-slim",
    memory: str = "128m",
    cpus: str = "0.5",
    pids_limit: int = 64,
    runtime: str | None = None,
    cap_add: tuple[str, ...] = (),
) -> tuple[str, list[str]]:
    cname = container_name or f"wf_sbx_{uuid.uuid4().hex[:10]}"
    cmd = [
        "docker", "run", "--rm",
        "--name", cname,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--tmpfs", "/tmp:size=16m,noexec,nosuid,nodev",  # nosec B108 — container-internal tmpfs
        f"--memory={memory}",
        f"--cpus={cpus}",
        f"--pids-limit={pids_limit}",
        "--security-opt=no-new-privileges",
        "--user", "65534:65534",
    ]
    for cap in cap_add:
        if cap not in ALLOWED_DOCKER_CAPS:
            raise ValueError(f"Disallowed Docker capability: {cap}")
        cmd.extend(["--cap-add", cap])
    chosen = runtime or os.getenv("DOCKER_SANDBOX_RUNTIME", "").strip()
    if chosen:
        cmd.append(f"--runtime={chosen}")
    cmd.extend([image, "python", "-c", python_code])
    return cname, cmd


def docker_python_runner(
    python_code: str,
    timeout_seconds: int = 10,
    image: str = "python:3.12-slim",
    runtime: str | None = None,
) -> dict[str, Any]:
    if timeout_seconds < 1 or timeout_seconds > 60:
        raise ValueError("timeout_seconds must be between 1 and 60.")
    if shutil.which("docker") is None:
        return {
            "isolated": True,
            "available": False,
            "passed": False,
            "stderr": "Docker CLI not found.",
        }

    cname, cmd = build_docker_sandbox_cmd(python_code, image=image, runtime=runtime)
    try:
        proc = subprocess.run(  # nosec B603 — argv built internally, no shell
            cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
        return {
            "isolated": True,
            "available": True,
            "container_name": cname,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "passed": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        # Actively kill the container so it does not keep running after CLI timeout
        subprocess.run(["docker", "kill", cname], capture_output=True, text=True, check=False)  # nosec B603, B607
        subprocess.run(["docker", "rm", "-f", cname], capture_output=True, text=True, check=False)  # nosec B603, B607
        return {
            "isolated": True,
            "available": True,
            "container_name": cname,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Docker Timeout ({timeout_seconds}s) — container killed",
            "passed": False,
        }
