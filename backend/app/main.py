from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, get_settings
from .db import Database
from .gateway import AllProvidersUnavailable, LLMGateway
from .schemas import ChatMetadata, ChatRequest, ChatResponse, HealthResponse
from .simulation import parse_failure_header

log = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.db = Database(settings.database_url)
        app.state.db.init()
        app.state.gateway = LLMGateway(settings)
        app.state.locks = {}
        log.info(
            "started: keys=%d model=%s cache=%s simulation=%s",
            app.state.gateway.keys_configured, settings.llm_model,
            settings.cache_enabled, settings.enable_failure_simulation,
        )
        yield

    app = FastAPI(title="LLM Chatbot API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # ---- JSON-only error handling (never HTML, never a stack trace) ----
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError):
        errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.exception_handler(AllProvidersUnavailable)
    async def providers_exc(_: Request, __: AllProvidersUnavailable):
        return JSONResponse({"detail": "all providers unavailable"}, status_code=503)

    @app.exception_handler(Exception)
    async def unhandled_exc(_: Request, exc: Exception):
        log.exception("unhandled error: %s", type(exc).__name__)
        return JSONResponse({"detail": "internal server error"}, status_code=500)

    # ---- Routes ----
    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request):
        gw: LLMGateway = request.app.state.gateway
        db_ok = await asyncio.to_thread(request.app.state.db.ping)
        ok = db_ok and gw.keys_configured >= 2
        body = {"status": "ok" if ok else "degraded", "keys_configured": gw.keys_configured,
                "cache_enabled": gw.cache_enabled}
        if not ok:
            body["detail"] = "database unreachable" if not db_ok else "at least 2 API keys are required"
        return JSONResponse(body, status_code=200 if ok else 503)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        req: ChatRequest,
        request: Request,
        x_simulate_failure: str | None = Header(default=None),
    ):
        db: Database = request.app.state.db
        gw: LLMGateway = request.app.state.gateway
        locks: dict = request.app.state.locks
        lock = locks.setdefault(req.session_id, asyncio.Lock())  # keep one session's turns ordered
        simulate = parse_failure_header(x_simulate_failure) if settings.enable_failure_simulation else None

        async with lock:
            history = await asyncio.to_thread(db.get_history, req.session_id)
            system_prompt = (req.system_prompt or "").strip() or None
            if system_prompt is None:
                system_prompt = await asyncio.to_thread(db.get_system_prompt, req.session_id)
            messages = [{"role": "system", "content": system_prompt or settings.default_system_prompt}]
            messages += [{"role": m["role"], "content": m["content"]} for m in history]
            messages.append({"role": "user", "content": req.message})

            result = await gw.complete(messages, simulate)  # raises AllProvidersUnavailable -> 503, nothing stored

            metadata = ChatMetadata(
                resolution_source="LLM_CACHE" if result.cache_hit else "LIVE_INFERENCE",
                model=result.model,
                latency_ms=result.latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                key_id=result.key_id,
                fallback_attempts=result.fallback_attempts,
            )
            await asyncio.to_thread(
                db.save_exchange, req.session_id, (req.system_prompt or "").strip() or None,
                req.message, result.reply, metadata.model_dump(),
            )
        if len(locks) > 5000:  # bound memory of the lock table
            locks.clear()
        return ChatResponse(session_id=req.session_id, reply=result.reply, metadata=metadata)

    @app.get("/sessions/{session_id}/messages")
    async def session_messages(session_id: str, request: Request):
        db: Database = request.app.state.db
        if not await asyncio.to_thread(db.session_exists, session_id):
            return JSONResponse({"detail": "session not found"}, status_code=404)
        messages = await asyncio.to_thread(db.get_history, session_id)
        return {"session_id": session_id, "messages": messages}

    return app


app = create_app()
