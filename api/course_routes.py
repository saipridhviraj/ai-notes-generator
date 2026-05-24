"""Multi-day course API — syllabus plan, batch generation, checkpoint reviews."""
import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import require_api_key
from api.course_models import (
    CourseActionResponse,
    CourseCheckpointRespondRequest,
    CourseListResponse,
    CoursePlanRequest,
    CoursePlanRespondRequest,
    CoursePlanResponse,
    CourseRetryDayRequest,
    CourseStatusResponse,
    CourseSummaryItem,
    DayPlanSummary,
)
from api.rate_limit import limiter
from services.course_planner import build_course_plan
from services.course_runner import course_output_root
from services.course_control import cancel_course_generation, launch_course_batch, resume_course_batch, retry_course_day
from utils.course_store import create_course, delete_all_courses, delete_course, get_course, list_courses, update_course
from utils.helpers import generate_session_id
from utils.job_health import course_batch_alive, course_interrupted

router = APIRouter(prefix="/course", tags=["course"])


@router.get("/courses", response_model=CourseListResponse, dependencies=[Depends(require_api_key)])
@limiter.exempt
async def list_course_runs(limit: int = 50):
    items = [CourseSummaryItem(**row) for row in list_courses(limit)]
    return CourseListResponse(courses=items)


@router.delete("/courses", response_model=CourseActionResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def delete_all_courses_route(request: Request):
    from utils.job_health import cancel_course_task

    for row in list_courses(limit=200):
        cancel_course_task(row["course_id"])

    count = delete_all_courses()
    return CourseActionResponse(
        course_id="*",
        status="deleted",
        message=f"Deleted {count} course(s).",
    )


def _progress_percent(course: dict) -> float:
    total = course.get("total_days") or 1
    done = len(course.get("days_completed", []))
    return round(100.0 * done / total, 1)


def _status_response(course: dict) -> CourseStatusResponse:
    plan = course.get("plan")
    plan_days = []
    if plan:
        plan_days = [
            DayPlanSummary(
                day=d.day,
                title=d.title,
                topic=d.topic,
                duration_minutes=d.duration_minutes,
            )
            for d in plan.days
        ]
    return CourseStatusResponse(
        course_id=course["course_id"],
        status=course["status"],
        course_name=course["course_name"],
        total_days=course["total_days"],
        days_completed=course.get("days_completed", []),
        next_day=course.get("next_day", 1),
        progress_percent=_progress_percent(course),
        output_root=course["output_root"],
        checkpoint_every=course.get("checkpoint_every", 4),
        hours_per_day=course.get("hours_per_day", 1.5),
        plan_days=plan_days,
        current_generating_day=course.get("current_generating_day"),
        current_day_title=course.get("current_day_title"),
        current_session_id=course.get("current_session_id"),
        checkpoint_message=course.get("checkpoint_message"),
        plan_summary=plan.syllabus_summary if plan else None,
        day_outputs=course.get("day_outputs", {}),
        day_sessions=course.get("day_sessions", {}),
        errors=course.get("errors", []),
        batch_active=course_batch_alive(course["course_id"])
        if course.get("status") == "generating"
        else None,
        interrupted=course_interrupted(course, course["course_id"]),
    )


@router.post(
    "/plan",
    response_model=CoursePlanResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def plan_course(request: Request, body: CoursePlanRequest):
    course_id = generate_session_id()
    output_root = str(course_output_root(body.course_name))

    create_course(
        course_id=course_id,
        course_name=body.course_name,
        syllabus=body.syllabus,
        total_days=body.total_days,
        hours_per_day=body.hours_per_day,
        checkpoint_every=body.checkpoint_every,
        programming_languages=body.programming_languages,
        output_root=output_root,
    )

    try:
        plan = await asyncio.to_thread(
            build_course_plan,
            body.syllabus,
            body.course_name,
            body.total_days,
            body.hours_per_day,
            body.programming_languages,
        )
    except Exception as e:
        update_course(course_id, status="failed", errors=[f"Course planning failed: {e}"])
        raise HTTPException(status_code=500, detail=f"Course planning failed: {e}") from e

    update_course(
        course_id,
        plan=plan,
        status="awaiting_plan_approval",
        course_name=plan.course_name,
        total_days=plan.total_days,
        hours_per_day=plan.hours_per_day,
        programming_languages=plan.programming_languages,
        output_root=str(course_output_root(plan.course_name)),
    )

    course = get_course(course_id)
    summaries = [
        DayPlanSummary(
            day=d.day,
            title=d.title,
            topic=d.topic,
            duration_minutes=d.duration_minutes,
        )
        for d in plan.days
    ]

    return CoursePlanResponse(
        course_id=course_id,
        status="awaiting_plan_approval",
        course_name=plan.course_name,
        total_days=plan.total_days,
        output_root=course["output_root"],
        days=summaries,
        message="30-day plan ready. Review and POST /course/{id}/plan/respond to approve.",
    )


@router.get("/{course_id}/status", response_model=CourseStatusResponse, dependencies=[Depends(require_api_key)])
async def course_status(course_id: str):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return _status_response(course)


@router.post(
    "/{course_id}/plan/respond",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_TUTOR", "10/minute"))
async def respond_to_plan(
    request: Request,
    course_id: str,
    body: CoursePlanRespondRequest,
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if course["status"] != "awaiting_plan_approval":
        raise HTTPException(status_code=400, detail=f"Course status is {course['status']}")

    if not body.approved:
        update_course(course_id, status="rejected", errors=[body.feedback or "Plan rejected"])
        return CourseActionResponse(
            course_id=course_id,
            status="rejected",
            message="Course plan rejected.",
        )

    update_course(course_id, status="generating", next_day=1, days_completed=[])
    launch_course_batch(course_id)
    course = get_course(course_id)

    return CourseActionResponse(
        course_id=course_id,
        status="generating",
        message=f"Plan approved. Generating days 1–{min(course['checkpoint_every'], course['total_days'])}…",
    )


@router.post(
    "/{course_id}/checkpoint/respond",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_TUTOR", "10/minute"))
async def respond_to_checkpoint(
    request: Request,
    course_id: str,
    body: CourseCheckpointRespondRequest,
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if course["status"] != "awaiting_checkpoint":
        raise HTTPException(status_code=400, detail=f"Course status is {course['status']}")

    if not body.approved:
        update_course(
            course_id,
            status="failed",
            errors=[body.feedback or "Checkpoint rejected by tutor"],
        )
        return CourseActionResponse(
            course_id=course_id,
            status="failed",
            message="Generation stopped after checkpoint rejection.",
        )

    update_course(course_id, status="generating", checkpoint_message=None)
    launch_course_batch(course_id)

    return CourseActionResponse(
        course_id=course_id,
        status="generating",
        message="Checkpoint approved. Resuming day generation…",
    )


@router.post(
    "/{course_id}/cancel",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def cancel_course(request: Request, course_id: str):
    try:
        course = cancel_course_generation(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CourseActionResponse(
        course_id=course_id,
        status=course["status"],
        message="Course generation paused.",
    )


@router.post(
    "/{course_id}/resume-batch",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def resume_course(request: Request, course_id: str):
    try:
        course = resume_course_batch(course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CourseActionResponse(
        course_id=course_id,
        status=course["status"],
        message="Resuming course day generation…",
    )


@router.post(
    "/{course_id}/retry-day",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def retry_day(request: Request, course_id: str, body: CourseRetryDayRequest):
    try:
        course = retry_course_day(course_id, body.day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    day = body.day or course.get("next_day", 1)
    return CourseActionResponse(
        course_id=course_id,
        status=course["status"],
        message=f"Retrying day {day}…",
    )


@router.delete(
    "/{course_id}",
    response_model=CourseActionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(os.getenv("RATE_LIMIT_GENERATE", "5/minute"))
async def delete_course_run(request: Request, course_id: str):
    from utils.helpers import get_session, set_session
    from utils.job_health import cancel_course_task
    from utils.stream_bus import clear_session

    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    cancel_course_task(course_id)

    sid = course.get("current_session_id")
    if sid:
        session = get_session(sid)
        if session:
            task = session.get("task")
            if task and not task.done():
                task.cancel()
            session["state"]["status"] = "cancelled"
            set_session(sid, session)
            clear_session(sid)

    if not delete_course(course_id):
        raise HTTPException(status_code=404, detail="Course not found.")

    return CourseActionResponse(
        course_id=course_id,
        status="deleted",
        message="Course removed from history.",
    )
