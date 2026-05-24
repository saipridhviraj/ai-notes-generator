import os
import pathlib
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.rate_limit import limiter

load_dotenv()


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from utils.stream_bus import set_event_loop
    from services.file_service import NOTES_DIR
    from services.prompt_config import get_prompt_profile
    from services.note_ready_publisher import is_enabled, retry_loop
    from graph.graph_builder import init_checkpointer, close_checkpointer
    from graph import reset_graph_cache

    set_event_loop(asyncio.get_running_loop())
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    await init_checkpointer()
    reset_graph_cache()
    print(f"[startup] Prompt profile: {get_prompt_profile()}", flush=True)
    if is_enabled():
        print("[startup] note.ready webhook enabled", flush=True)
    from graph import graph  # noqa: F401 — compiles graph + loads examples

    stop_retry = asyncio.Event()
    retry_task = None
    if is_enabled():
        retry_task = asyncio.create_task(retry_loop(stop_retry))

    from utils.job_health import reconcile_stale_jobs_on_startup
    await reconcile_stale_jobs_on_startup()

    yield

    if retry_task is not None:
        stop_retry.set()
        await retry_task
    await close_checkpointer()
    reset_graph_cache()


app = FastAPI(
    title="AI Notes Generator",
    description=(
        "Agentic AI backend that generates student and tutor Markdown notes "
        "using LangGraph + Groq + Tavily."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import router  # noqa: E402
from api.course_routes import router as course_router  # noqa: E402
from api.note_events_routes import router as note_events_router  # noqa: E402

app.include_router(router)
app.include_router(course_router)
app.include_router(note_events_router)

_FRONTEND_DIST = pathlib.Path(__file__).parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _serve_spa(full_path: str):
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
