import asyncio
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from api.auth import require_api_key
from api.rate_limit import limiter
from api.models import (
    GenerateRequest,
    GenerateResponse,
    StatusResponse,
    TutorRespondRequest,
    TutorRespondResponse,
    ResultResponse,
    HealthResponse,
    CancelResponse,
    NodeArtifactResponse,
    ResumeRequest,
    ResumeResponse,
    RestartResponse,
    SessionListResponse,
    SessionSummaryItem,
    SessionChatRequest,
    SessionChatResponse,
    ChatMessageItem,
    DeleteSessionResponse,
    BulkDeleteResponse,
)
from utils.helpers import (
    create_session,
    get_session,
    set_session,
    get_graph_config,
    generate_session_id,
    session_store,
)
from utils.node_artifacts import get_node_artifact_content
from utils.status_events import build_status_payload
from utils.graph_runner import consume_graph_stream
from utils.graph_resume import (
    build_resume_state_patch,
    get_resume_goto,
    validate_resume_request,
)

router = APIRouter()


def _build_initial_state(topic: str, session_id: str) -> dict:
    return {
        "user_input": topic,
        "session_id": session_id,
        "planner_output": None,
        "planner_verified": False,
        "planner_feedback": None,
        "tutor_question": None,
        "tutor_response": None,
        "awaiting_tutor": False,
        "research_data": None,
        "used_web_search": False,
        "student_notes": None,
        "tutor_notes": None,
        "student_filename": None,
        "tutor_filename": None,
        "evaluation_result": None,
        "retry_count": 0,
        "output_files": [],
        "final_summary": None,
        "errors": [],
        "status": "running",
        "output_dir": None,
        "course_day": None,
        "course_id": None,
        "chat_history": [],
    }


@router.get("/app-config", include_in_schema=False)
async def app_config():
    """Return runtime config for the frontend (no auth required — same-origin only)."""
    return {"api_key": os.getenv("APP_API_KEY", "")}


@router.post("/generate", response_model=GenerateResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def generate(request: Request, body: GenerateRequest):
    from graph import graph

    session_id = body.session_id or generate_session_id()
    initial_state = _build_initial_state(body.topic, session_id)
    create_session(session_id, initial_state)

    async def run_graph():
        config = get_graph_config(session_id)
        stream = graph.astream(initial_state, config=config, stream_mode="updates")
        await consume_graph_stream(session_id, stream)

    task = asyncio.create_task(run_graph())
    session_store[session_id]["task"] = task

    return GenerateResponse(
        session_id=session_id,
        status="running",
        message=f"Note generation started. Connect to /status-stream/{session_id} for live updates.",
    )


@router.get("/sessions", response_model=SessionListResponse, dependencies=[Depends(require_api_key)])
@limiter.exempt
async def list_sessions(limit: int = 50):
    from utils.session_store import list_sessions as _list_sessions

    items = [SessionSummaryItem(**row) for row in _list_sessions(limit)]
    return SessionListResponse(sessions=items)


@router.delete("/sessions", response_model=BulkDeleteResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def delete_all_sessions_route(request: Request):
    from utils.session_store import delete_all_sessions as _delete_all

    count = _delete_all()
    return BulkDeleteResponse(
        deleted_count=count,
        message=f"Deleted {count} conversation(s).",
    )


@router.post(
    "/sessions/{session_id}/chat",
    response_model=SessionChatResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def session_chat(request: Request, session_id: str, body: SessionChatRequest):
    from services.session_chat import handle_session_chat

    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    task = session.get("task")
    if task is not None and not task.done():
        raise HTTPException(status_code=400, detail="Session is still running.")

    state = session["state"]
    try:
        patch = await asyncio.to_thread(handle_session_chat, state, body.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    state = {**state, **patch}
    session["state"] = state
    set_session(session_id, session)

    history = [ChatMessageItem(**item) for item in state.get("chat_history", [])]
    return SessionChatResponse(
        session_id=session_id,
        message="Notes updated and saved.",
        status=state.get("status", "completed"),
        output_files=state.get("output_files", []),
        chat_history=history,
    )


@router.delete(
    "/sessions/{session_id}/chat",
    response_model=SessionChatResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def clear_session_chat_history(request: Request, session_id: str):
    from utils.session_store import clear_session_chat, get_session as _get_session_store

    session = _get_session_store(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        clear_session_chat(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    session = _get_session_store(session_id)
    state = session["state"] if session else {}
    return SessionChatResponse(
        session_id=session_id,
        message="Edit chat history cleared.",
        status=state.get("status", "completed"),
        output_files=state.get("output_files", []),
        chat_history=[],
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def delete_session_route(request: Request, session_id: str):
    from utils.session_store import delete_session as _delete_session, get_session as _get_session_store

    if not _get_session_store(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    _delete_session(session_id)
    return DeleteSessionResponse(session_id=session_id, message="Conversation deleted.")


@router.get("/status/{session_id}", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
@limiter.exempt
async def get_status(session_id: str):
    payload = build_status_payload(session_id)
    if not payload:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )
    return StatusResponse(**payload)


@router.get("/status-stream/{session_id}", dependencies=[Depends(require_api_key)])
@limiter.exempt
async def stream_session_status(session_id: str):
    """SSE stream of pipeline status — one event per state change (replaces polling)."""
    if not get_session(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    from utils.stream_bus import subscribe_status

    async def event_generator():
        initial = build_status_payload(session_id)
        if initial:
            yield f"data: {json.dumps({'type': 'status', 'data': initial})}\n\n"
            if initial.get("status") in {
                "completed",
                "failed",
                "max_retries_reached",
                "rejected",
                "cancelled",
            }:
                return

        try:
            async for event in subscribe_status(session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/artifacts/{session_id}/{node_id}",
    response_model=NodeArtifactResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.exempt
async def get_node_artifact(session_id: str, node_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    payload = get_node_artifact_content(session["state"], node_id)
    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"No output available yet for node '{node_id}'.",
        )
    return NodeArtifactResponse(**payload)


@router.post(
    "/cancel/{session_id}",
    response_model=CancelResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def cancel_session(request: Request, session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    state = session["state"]
    if state.get("status") in ("completed", "cancelled", "rejected"):
        raise HTTPException(status_code=400, detail=f"Session already {state.get('status')}")

    task = session.get("task")
    if task and not task.done():
        task.cancel()

    session["state"]["status"] = "cancelled"
    set_session(session_id, session)

    from utils.stream_bus import clear_session
    clear_session(session_id)

    return CancelResponse(
        session_id=session_id,
        status="cancelled",
        message="Generation cancelled.",
    )


@router.post(
    "/resume/{session_id}",
    response_model=ResumeResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def resume_from_node(request: Request, session_id: str, body: ResumeRequest):
    """
    Re-run the pipeline from a specific node using existing session state.

    Example: tutor JSON failed but student_notes is good → from_node=tutor_notes
    """
    from graph import graph
    from langgraph.types import Command

    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    state = session["state"]
    err = validate_resume_request(state, body.from_node)
    if err:
        raise HTTPException(status_code=400, detail=err)

    task = session.get("task")
    if task and not task.done():
        raise HTTPException(
            status_code=400,
            detail="Session is still running. Cancel it first, then resume.",
        )

    patch = build_resume_state_patch(state, body.from_node)
    merged = {**state, **patch}
    session["state"] = merged
    session["state"]["status"] = "running"
    set_session(session_id, session)

    as_node, goto = get_resume_goto(body.from_node)
    config = get_graph_config(session_id)

    async def run_resume():
        try:
            await graph.aupdate_state(config, merged, as_node=as_node)
            stream = graph.astream(Command(goto=goto), config=config, stream_mode="updates")
            await consume_graph_stream(session_id, stream)
        except Exception as e:
            s = get_session(session_id)
            if s:
                s["state"]["status"] = "failed"
                s["state"]["errors"].append(f"Resume from {body.from_node} failed: {e}")
                set_session(session_id, s)

    from utils.stream_bus import clear_session
    clear_session(session_id)

    new_task = asyncio.create_task(run_resume())
    session_store[session_id]["task"] = new_task

    return ResumeResponse(
        session_id=session_id,
        from_node=body.from_node,
        status="running",
        message=f"Resuming from {body.from_node}. Connect to /status-stream/{session_id} for live updates.",
    )


@router.post(
    "/restart/{session_id}",
    response_model=RestartResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def restart_session(request: Request, session_id: str):
    """Resume a session whose graph task died (e.g. after server restart)."""
    from graph import graph
    from utils.job_health import session_interrupted, session_task_alive

    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    if session_task_alive(session):
        raise HTTPException(status_code=400, detail="Session is already running.")

    state = session["state"]
    if state.get("status") not in ("running",) and not session_interrupted(session):
        raise HTTPException(
            status_code=400,
            detail=f"Session cannot restart from status {state.get('status')}",
        )

    session["state"]["status"] = "running"
    set_session(session_id, session)

    async def run_restart():
        config = get_graph_config(session_id)
        try:
            stream = graph.astream(None, config=config, stream_mode="updates")
            await consume_graph_stream(session_id, stream)
        except Exception:
            s = get_session(session_id)
            if s:
                stream = graph.astream(s["state"], config=config, stream_mode="updates")
                await consume_graph_stream(session_id, stream)

    from utils.stream_bus import clear_session
    clear_session(session_id)

    new_task = asyncio.create_task(run_restart())
    session_store[session_id]["task"] = new_task

    return RestartResponse(
        session_id=session_id,
        status="running",
        message="Generation restarted. Connect to /status-stream/{session_id} for live updates.",
    )


@router.get("/stream/{session_id}")
@limiter.exempt
async def stream_llm_tokens(session_id: str, _key: str = Depends(require_api_key)):
    """Server-Sent Events stream of LLM tokens for a running session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    from utils.stream_bus import subscribe

    async def event_generator():
        try:
            async for event in subscribe(session_id):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tutor/respond/{session_id}", response_model=TutorRespondResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(os.getenv("RATE_LIMIT_TUTOR", "10/minute"))
async def tutor_respond(request: Request, session_id: str, body: TutorRespondRequest):
    from graph import graph

    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    state = session["state"]
    if state.get("status") != "awaiting_tutor":
        raise HTTPException(
            status_code=400,
            detail="Session is not awaiting tutor input",
        )

    if body.approved and body.feedback:
        response_text = f"approved with feedback: {body.feedback}"
    elif body.approved:
        response_text = "approved"
    else:
        response_text = f"rejected: {body.feedback or 'no reason given'}"

    session["state"]["tutor_response"] = response_text
    session["state"]["response_to"] = body.response_to
    session["state"]["status"] = "running"
    set_session(session_id, session)

    # Resume the graph from the last checkpoint using LangGraph 1.x Command API
    async def resume_graph():
        from langgraph.types import Command
        config = get_graph_config(session_id)
        resume_value = response_text
        stream = graph.astream(
            Command(resume=resume_value), config=config, stream_mode="updates"
        )
        await consume_graph_stream(session_id, stream)

    task = asyncio.create_task(resume_graph())
    session_store[session_id]["task"] = task

    return TutorRespondResponse(
        session_id=session_id,
        message="Tutor response received. Resuming generation.",
        status="running",
    )


@router.get("/result/{session_id}", response_model=ResultResponse, dependencies=[Depends(require_api_key)])
async def get_result(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. If the server was restarted, click Start new and generate again.",
        )

    state = session["state"]
    eval_score = None
    if state.get("evaluation_result"):
        er = state["evaluation_result"]
        eval_score = {
            "student": er.student_notes_score,
            "tutor":   er.tutor_notes_score,
        }

    plan = state.get("planner_output")
    session_status = state.get("status", "running")
    include_notes = session_status in ("completed", "max_retries_reached")
    return ResultResponse(
        session_id=session_id,
        status=session_status,
        topic=plan.topic if plan else None,
        student_file=state.get("student_filename"),
        tutor_file=state.get("tutor_filename"),
        student_markdown=state.get("student_notes") if include_notes else None,
        tutor_markdown=state.get("tutor_notes") if include_notes else None,
        evaluation_score=eval_score,
        retry_count=state.get("retry_count", 0),
        used_web_search=state.get("used_web_search", False),
        summary=state.get("final_summary"),
    )


@router.get("/health", response_model=HealthResponse)
async def health():
    from services.llm_config import get_provider_name
    from services.prompt_config import get_prompt_profile
    from services.llm_client import check_ollama_reachable
    from services.note_ready_publisher import is_enabled
    from utils import note_event_outbox as outbox

    ollama_ok = check_ollama_reachable()
    status = "ok"
    if ollama_ok is False:
        status = "degraded"

    note_ready_on = is_enabled()
    return HealthResponse(
        status=status,
        version="1.0.0",
        llm_provider=get_provider_name(),
        prompt_profile=get_prompt_profile(),
        ollama_reachable=ollama_ok,
        note_ready_enabled=note_ready_on,
        note_ready_pending=outbox.count_by_status("pending") if note_ready_on else None,
    )
