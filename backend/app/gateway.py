"""LiteLLM gateway: key pool, automatic fallback, built-in cache, failure simulation.

Design
------
* One LiteLLM Router "model group" per API key (key_1, key_2, ...), each with exactly one deployment
  whose model_info.id is the key id. That makes key attribution deterministic.
* The Router's own `fallbacks` option chains key_1 -> key_2 -> ... so LiteLLM performs the failover.
* LiteLLM's global cache (in-memory or disk) is shared across the groups through `caching_groups`, so
  the cache identity is (model namespace + full message list) and NOT the key that answered.
* A CustomLogger pre-call hook runs right before every real provider attempt. It records the attempt
  (for fallback_attempts) and injects the simulated failure from X-Simulate-Failure for that attempt.
"""
from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

import litellm
from litellm import Router
from litellm.integrations.custom_logger import CustomLogger

from .config import Settings

log = logging.getLogger("app.gateway")

_attempts: ContextVar[Optional[list]] = ContextVar("llm_attempts", default=None)
_simulation: ContextVar[Optional[dict]] = ContextVar("llm_simulation", default=None)


class AllProvidersUnavailable(Exception):
    pass


def _simulated_error(status: int, model: str) -> Exception:
    msg = f"simulated provider failure ({status})"
    cls = {
        429: litellm.RateLimitError,
        500: litellm.InternalServerError,
        502: litellm.BadGatewayError,
        503: litellm.ServiceUnavailableError,
    }[status]
    return cls(message=msg, llm_provider="simulated", model=model)


_SECRETS: list[str] = []


def redact(text: str) -> str:
    """Remove any configured API key value from text before it is logged or printed."""
    for secret in _SECRETS:
        if secret:
            text = text.replace(secret, "***")
    return text


def describe_error(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    msg = redact(str(exc)).replace("\n", " ")[:300]
    return f"{type(exc).__name__} status={status} msg={msg}"


class _AttemptHook(CustomLogger):
    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        key_id = (kwargs.get("model_info") or {}).get("id")
        exc = kwargs.get("exception")
        if key_id and exc is not None:
            log.warning("provider attempt failed key=%s %s", key_id, describe_error(exc))

    async def async_pre_call_deployment_hook(self, kwargs, call_type):
        key_id = (kwargs.get("model_info") or {}).get("id")
        attempts = _attempts.get()
        if attempts is not None and key_id:
            attempts.append(key_id)
        sim = _simulation.get()
        if sim and key_id:
            status = sim.get(key_id, sim.get("*"))
            if status:
                raise _simulated_error(status, str(kwargs.get("model")))
        return None


@dataclass
class GatewayResult:
    reply: str
    model: str
    input_tokens: int
    output_tokens: int
    key_id: Optional[str]
    fallback_attempts: int
    cache_hit: bool
    latency_ms: int


class LLMGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.llm_model
        keys = settings.api_keys
        _SECRETS[:] = keys
        self.key_ids = [f"key_{i}" for i in range(1, len(keys) + 1)]
        self.cache_enabled = settings.cache_enabled

        litellm.suppress_debug_info = True
        litellm.set_verbose = False
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)
        logging.getLogger("LiteLLM Router").setLevel(logging.WARNING)

        # Reset global state so a fresh gateway always starts with a fresh cache and a single hook.
        litellm.cache = None
        litellm.callbacks = [c for c in litellm.callbacks if not isinstance(c, _AttemptHook)]
        litellm.callbacks.append(_AttemptHook())
        if self.cache_enabled:
            if settings.cache_type == "disk":
                litellm.enable_cache(type="disk", disk_cache_dir=settings.cache_dir)
            else:
                litellm.enable_cache(type="local")

        self.router: Optional[Router] = None
        if keys:
            model_list = [
                {
                    "model_name": kid,
                    "litellm_params": {"model": self.model, "api_key": key, "timeout": settings.llm_timeout_seconds},
                    "model_info": {"id": kid},
                }
                for kid, key in zip(self.key_ids, keys)
            ]
            fallbacks = [{kid: self.key_ids[i + 1:]} for i, kid in enumerate(self.key_ids[:-1])]
            self.router = Router(
                model_list=model_list,
                fallbacks=fallbacks,
                cache_responses=self.cache_enabled,
                num_retries=0,  # no same-key retries: every failure moves to the next key
                disable_cooldowns=True,  # a rate-limited key is retried on the next request
                caching_groups=[tuple(self.key_ids)] if self.cache_enabled else None,
            )

    @property
    def keys_configured(self) -> int:
        return len(self.key_ids)

    async def complete(self, messages: list[dict], simulate: Optional[dict] = None) -> GatewayResult:
        if self.router is None:
            raise AllProvidersUnavailable()
        attempts: list[str] = []
        t_attempts = _attempts.set(attempts)
        t_sim = _simulation.set(simulate or None)
        cache_ctl = {"namespace": self.model}
        if simulate:
            cache_ctl["no-cache"] = True  # simulated requests must really exercise provider fallback
        started = time.perf_counter()
        try:
            resp = await self.router.acompletion(model=self.key_ids[0], messages=messages, cache=cache_ctl)
        except Exception as exc:  # every key failed (or a non-retryable error): never leak details
            log.warning("all providers failed; last error: %s", describe_error(exc))
            raise AllProvidersUnavailable() from exc
        finally:
            _attempts.reset(t_attempts)
            _simulation.reset(t_sim)
        latency_ms = int((time.perf_counter() - started) * 1000)

        hidden = getattr(resp, "_hidden_params", {}) or {}
        cache_hit = hidden.get("cache_hit") is True
        reply = (resp.choices[0].message.content or "").strip()
        if not reply:
            raise AllProvidersUnavailable()

        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None)
        out_tok = getattr(usage, "completion_tokens", None)
        if in_tok is None or out_tok is None:
            # Provider did not report usage: fall back to LiteLLM's tokenizer (documented in README).
            log.warning("provider returned no usage; estimating with litellm.token_counter")
            in_tok = litellm.token_counter(model=self.model, messages=messages)
            out_tok = litellm.token_counter(model=self.model, text=reply)

        if cache_hit:
            key_id, fallbacks = None, 0
        else:
            key_id = attempts[-1] if attempts else None
            fallbacks = max(len(attempts) - 1, 0)
        return GatewayResult(
            reply=reply,
            model=self.model,
            input_tokens=int(in_tok),
            output_tokens=int(out_tok),
            key_id=key_id,
            fallback_attempts=fallbacks,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
        )
