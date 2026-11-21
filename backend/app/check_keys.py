"""Diagnostic: one tiny real request per configured key. Never prints key values.

Run inside the container:  docker compose exec backend python -m app.check_keys
"""
from __future__ import annotations

import asyncio

import litellm

from .config import get_settings
from .gateway import describe_error, _SECRETS


async def main() -> int:
    s = get_settings()
    keys = s.api_keys
    _SECRETS[:] = keys
    litellm.suppress_debug_info = True
    print(f"model: {s.llm_model}")
    print(f"keys configured: {len(keys)}")
    if not keys:
        print("No keys found in LLM_API_KEYS.")
        return 2
    ok = 0
    for i, key in enumerate(keys, 1):
        label = f"key_{i}"
        if key.lower().startswith(("replace", "your", "xxx")) or len(key) < 20:
            print(f"{label}: looks like a placeholder (length {len(key)}) - skipped")
            continue
        try:
            r = await litellm.acompletion(
                model=s.llm_model, api_key=key, max_tokens=16, timeout=s.llm_timeout_seconds,
                messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            )
            print(f"{label}: OK  reply={(r.choices[0].message.content or '').strip()[:40]!r} usage={r.usage.prompt_tokens}/{r.usage.completion_tokens}")
            ok += 1
        except Exception as exc:
            print(f"{label}: FAILED  {describe_error(exc)}")
    print(f"{ok}/{len(keys)} keys usable")
    return 0 if ok == len(keys) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
