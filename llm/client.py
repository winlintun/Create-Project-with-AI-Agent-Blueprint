"""
Provider-Agnostic LLM Adapter (`llm/client.py`)
- Supports Anthropic Messages API (`x-api-key`, `anthropic-version: 2023-06-01`),
  Gemini (`x-goog-api-key` header — NEVER `?key=` in URL), OpenAI, Groq, Ollama, Mock.
- Uses `httpx` when installed (graceful `urllib.request` fallback for zero-dep envs).
- Includes exponential backoff retry for HTTP 429 / 5xx rate limits & transient errors.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

DEFAULT_TIER_1_AGENTS = {"assistant_ai", "manager_ai"}
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


@dataclass
class LLMResponse:
    provider: str
    model: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class ProviderSpec:
    provider: str
    model: str
    api_key_env: str = ""
    base_url_env: str = ""
    base_url: str = ""
    cost_per_1k_input_usd: float = 0.0
    cost_per_1k_output_usd: float = 0.0


def _parse_scalar(val: str) -> Any:
    v = val.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


def _stdlib_parse_model_tiers_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_tier: str | None = None
    current_section: str | None = None
    current_model: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":"):
            current_tier = stripped[:-1]
            data[current_tier] = {"agents": [], "models": []}
            current_section = None
            current_model = None
        elif current_tier and indent == 2 and ":" in stripped:
            k, v = stripped.split(":", 1)
            k = k.strip()
            if k in {"agents", "models"}:
                current_section = k
                current_model = None
            else:
                data[current_tier][k] = _parse_scalar(v)
                current_section = None
        elif current_tier and current_section == "agents" and stripped.startswith("- "):
            data[current_tier]["agents"].append(_parse_scalar(stripped[2:]))
        elif current_tier and current_section == "models":
            if stripped.startswith("- "):
                current_model = {}
                data[current_tier]["models"].append(current_model)
                rest = stripped[2:].strip()
                if ":" in rest:
                    mk, mv = rest.split(":", 1)
                    current_model[mk.strip()] = _parse_scalar(mv)
            elif current_model is not None and ":" in stripped:
                mk, mv = stripped.split(":", 1)
                current_model[mk.strip()] = _parse_scalar(mv)
    return data


def load_tier_config(config_path: Path = Path("config/model_tiers.yaml")) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Tier config not found: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    if HAS_YAML:
        loaded = yaml.safe_load(text)
        return dict(loaded) if isinstance(loaded, dict) else {}
    return _stdlib_parse_model_tiers_yaml(text)


def _spec_from_dict(m: dict[str, Any]) -> ProviderSpec:
    base_url_env = str(m.get("base_url_env", ""))
    resolved_base_url = os.getenv(base_url_env, "") if base_url_env else str(m.get("base_url", ""))
    return ProviderSpec(
        provider=str(m["provider"]),
        model=str(m["model"]),
        api_key_env=str(m.get("api_key_env", "")),
        base_url_env=base_url_env,
        base_url=resolved_base_url,
        cost_per_1k_input_usd=float(m.get("cost_per_1k_input_usd", 0.0)),
        cost_per_1k_output_usd=float(m.get("cost_per_1k_output_usd", 0.0)),
    )


def _retry_delay(retry_after: str | None, attempt: int, backoff_base: float) -> float:
    if retry_after:
        try:
            return min(30.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return backoff_base * (2**attempt)


def _post_json_with_retry(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    timeout_seconds: int = 30,
    max_retries: int = 2,
    backoff_base: float = 0.5,
) -> dict[str, Any]:
    """POST JSON via httpx/urllib with Retry-After support and fail-fast on 4xx."""
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                        ra = resp.headers.get("Retry-After")
                        time.sleep(_retry_delay(ra, attempt, backoff_base))
                        continue
                    if 400 <= resp.status_code < 500:
                        raise RuntimeError(f"Non-retryable HTTP {resp.status_code} from {url}")
                    resp.raise_for_status()
                    return dict(resp.json())
            raw = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=raw, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout_seconds) as uresp:  # nosec B310
                return dict(json.loads(uresp.read().decode("utf-8")))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                ra = exc.headers.get("Retry-After") if exc.headers else None
                time.sleep(_retry_delay(ra, attempt, backoff_base))
                continue
            raise RuntimeError(f"HTTP {exc.code} from {url}") from None
        except RuntimeError:
            raise
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(backoff_base * (2**attempt))
                continue
            raise
    raise RuntimeError(f"HTTP request failed after retries: {last_err}")


def _calc_cost(spec: ProviderSpec, in_tok: int, out_tok: int) -> float:
    in_cost = (in_tok / 1000.0) * spec.cost_per_1k_input_usd
    out_cost = (out_tok / 1000.0) * spec.cost_per_1k_output_usd
    return round(in_cost + out_cost, 6)


class LLMClient:
    def __init__(
        self,
        providers: list[ProviderSpec] | None = None,
        *,
        tier1_providers: list[ProviderSpec] | None = None,
        tier2_providers: list[ProviderSpec] | None = None,
        tier1_agents: set[str] | None = None,
        timeout_seconds: int = 30,
        http_post_fn: Callable[..., dict[str, Any]] | None = None,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> None:
        self.providers = providers or [ProviderSpec(provider="mock", model="mock-local")]
        self.tier1_providers = tier1_providers or list(self.providers)
        self.tier2_providers = tier2_providers or list(self.providers)
        self.tier1_agents = set(DEFAULT_TIER_1_AGENTS if tier1_agents is None else tier1_agents)
        self.timeout_seconds = timeout_seconds
        self._http_post = http_post_fn or _post_json_with_retry
        self.custom_handlers = custom_handlers or {}

    @classmethod
    def from_config(
        cls,
        config_path: Path = Path("config/model_tiers.yaml"),
        *,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> LLMClient:
        cfg = load_tier_config(config_path)
        t1 = [_spec_from_dict(m) for m in cfg["tier_1_orchestrators"]["models"]]
        t2 = [_spec_from_dict(m) for m in cfg["tier_2_staff_executors"]["models"]]
        t1_agents = set(cfg["tier_1_orchestrators"]["agents"])
        return cls(
            providers=t1,
            tier1_providers=t1,
            tier2_providers=t2,
            tier1_agents=t1_agents,
            custom_handlers=custom_handlers,
        )

    @classmethod
    def with_tier_specs(
        cls,
        *,
        tier1_providers: list[ProviderSpec],
        tier2_providers: list[ProviderSpec],
        tier1_agents: set[str] | None = None,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> LLMClient:
        return cls(
            providers=tier1_providers,
            tier1_providers=tier1_providers,
            tier2_providers=tier2_providers,
            tier1_agents=tier1_agents,
            custom_handlers=custom_handlers,
        )

    def for_agent(self, agent_name: str) -> LLMClient:
        chosen = self.tier1_providers if agent_name in self.tier1_agents else self.tier2_providers
        return LLMClient(
            providers=list(chosen),
            tier1_providers=list(self.tier1_providers),
            tier2_providers=list(self.tier2_providers),
            tier1_agents=set(self.tier1_agents),
            timeout_seconds=self.timeout_seconds,
            http_post_fn=self._http_post,
            custom_handlers=self.custom_handlers,
        )

    def complete(self, system_prompt: str, user_message: str) -> LLMResponse:
        errors: list[str] = []
        for spec in self.providers:
            try:
                return self._call_provider(spec, system_prompt, user_message)
            except Exception as exc:  # noqa: BLE001 — record error, try next provider
                errors.append(f"{spec.provider}({spec.model}): {type(exc).__name__}: {exc}")
        raise RuntimeError("LLM Fallback Chain failed -> " + " | ".join(errors))

    def _call_provider(
        self, spec: ProviderSpec, system_prompt: str, user_message: str
    ) -> LLMResponse:
        if spec.provider in self.custom_handlers:
            return self.custom_handlers[spec.provider](spec, system_prompt, user_message)

        if spec.provider == "mock":
            in_tok = max(1, (len(system_prompt) + len(user_message)) // 4)
            text = f"[Mock:{spec.model}] {user_message[:120]}"
            out_tok = max(1, len(text) // 4)
            return LLMResponse("mock", spec.model, text, in_tok, out_tok, 0.0)

        if spec.provider == "anthropic":
            api_key = os.getenv(spec.api_key_env or "ANTHROPIC_API_KEY", "")
            if not api_key:
                raise OSError("Missing ANTHROPIC_API_KEY")
            data = self._http_post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                payload={
                    "model": spec.model,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usage", {})
            in_tok = int(usage.get("input_tokens", 0))
            out_tok = int(usage.get("output_tokens", 0))
            text = data["content"][0]["text"]
            return LLMResponse(
                "anthropic", spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider == "gemini":
            api_key = os.getenv(spec.api_key_env or "GEMINI_API_KEY", "")
            if not api_key:
                raise OSError("Missing GEMINI_API_KEY")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{spec.model}:generateContent"
            )
            data = self._http_post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                payload={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_message}]}],
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usageMetadata", {})
            in_tok = int(usage.get("promptTokenCount", 0))
            out_tok = int(usage.get("candidatesTokenCount", 0))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResponse(
                "gemini", spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider in {"openai", "groq"}:
            env_key = spec.api_key_env or (
                "GROQ_API_KEY" if spec.provider == "groq" else "OPENAI_API_KEY"
            )
            api_key = os.getenv(env_key, "")
            if not api_key:
                raise OSError(f"Missing {env_key}")
            url = (
                "https://api.groq.com/openai/v1/chat/completions"
                if spec.provider == "groq"
                else "https://api.openai.com/v1/chat/completions"
            )
            data = self._http_post(
                url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                payload={
                    "model": spec.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usage", {})
            in_tok = int(usage.get("prompt_tokens", 0))
            out_tok = int(usage.get("completion_tokens", 0))
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(
                spec.provider, spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider == "ollama":
            url_env = spec.base_url_env or "OLLAMA_BASE_URL"
            default_url = os.getenv(url_env, "http://127.0.0.1:11434")
            base = (spec.base_url or default_url).rstrip("/")
            data = self._http_post(
                f"{base}/api/chat",
                headers={"Content-Type": "application/json"},
                payload={
                    "model": spec.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
                timeout_seconds=self.timeout_seconds,
            )
            return LLMResponse("ollama", spec.model, data.get("message", {}).get("content", ""))

        raise ValueError(f"Unsupported LLM provider: {spec.provider}")
