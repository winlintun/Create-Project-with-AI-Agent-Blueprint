#!/usr/bin/env bash
set -euo pipefail
command -v docker >/dev/null 2>&1 || { echo "Docker not installed — skipping."; exit 0; }
docker run --rm --network=none --read-only --cap-drop=ALL   --tmpfs /tmp:size=16m,noexec,nosuid,nodev   --memory=128m --cpus=0.5 --pids-limit=64   --security-opt=no-new-privileges --user 65534:65534   python:3.12-slim python -c "print('DOCKER_SANDBOX_OK')"
