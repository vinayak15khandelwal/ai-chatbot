from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, StringConstraints


class ChatRequest(BaseModel):
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    system_prompt: Optional[Annotated[str, StringConstraints(max_length=8000)]] = None


class ChatMetadata(BaseModel):
    resolution_source: Literal["LIVE_INFERENCE", "LLM_CACHE"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str]
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class HealthResponse(BaseModel):
    status: str
    keys_configured: int
    cache_enabled: bool


class StoredMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    metadata: Optional[dict] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[StoredMessage]
