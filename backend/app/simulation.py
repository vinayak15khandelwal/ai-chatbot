"""Parser for the X-Simulate-Failure request header (e.g. 'key_1=429,key_2=500' or '*=429')."""
from __future__ import annotations

from typing import Optional

ALLOWED_STATUSES = {429, 500, 502, 503}


def parse_failure_header(value: Optional[str]) -> dict[str, int]:
    """Return {key_id or '*': status}. Malformed pairs are ignored."""
    result: dict[str, int] = {}
    if not value:
        return result
    for pair in value.split(","):
        if "=" not in pair:
            continue
        key, _, status = pair.partition("=")
        key, status = key.strip(), status.strip()
        if key and status.isdigit() and int(status) in ALLOWED_STATUSES:
            result[key] = int(status)
    return result
