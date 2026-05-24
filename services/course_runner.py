"""Orchestrate multi-day course generation with checkpoint pauses."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from graph.course_models import CoursePlan, DayPlan
from services.file_service import NOTES_DIR
from utils.course_store import get_course, set_course
from utils.helpers import create_session, generate_session_id, get_graph_config, get_session, set_session, slugify

logger = logging.getLogger(__name__)


def course_output_root(course_name: str) -> Path:
    return NOTES_DIR / slugify(course_name)


def day_output_dir(course: dict, day: DayPlan) -> Path:
    folder = f"day-{day.day:02d}-{slugify(day.title)}"
    return Path(course["output_root"]) / folder


def build_day_user_input(day: DayPlan, course: dict) -> str:
    concepts = ", ".join(day.concepts) if day.concepts else day.topic
    langs = day.programming_languages or course.get("programming_languages") or []
    lang_str = ", ".join(langs) if langs else "as appropriate"
    return (
        f"Course day {day.day}: {day.title}\n"
        f"Session length: {day.duration_minutes} minutes ({course['hours_per_day']} hours).\n"
        f"Concepts to cover: {concepts}\n"
        f"Programming languages / tools: {lang_str}\n"
        f"Focus: {day.topic}\n\n"
        "Tutor guide must include: in-class quiz (3–5 questions), homework assignment, "
        "and pacing notes for a 90-minute session."
    )


def _build_day_initial_state(day: DayPlan, course: dict, session_id: str) -> dict:
    out_dir = str(day_output_dir(course, day))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    return {
        "user_input": build_day_user_input(day, course),
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
        "output_dir": out_dir,
        "course_day": day.day,
        "course_id": course["course_id"],
    }


async def run_day_graph(session_id: str, initial_state: dict) -> str:
    """Run the notes graph to completion for one course day. Returns final status."""
    from graph import graph

    config = get_graph_config(session_id)
    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
            session = get_session(session_id)
            if session and session["state"].get("status") == "cancelled":
                break
            node_name = list(event.keys())[0]
            if node_name.startswith("__"):
                if node_name == "__interrupt__":
                    session = get_session(session_id)
                    if session:
                        session["state"]["status"] = "awaiting_tutor"
                        set_session(session_id, session)
                continue
            node_output = event[node_name]
            session = get_session(session_id)
            if session and isinstance(node_output, dict):
                session["state"].update(node_output)
                session["current_node"] = node_name
                set_session(session_id, session)
    except asyncio.CancelledError:
        session = get_session(session_id)
        if session:
            session["state"]["status"] = "cancelled"
            set_session(session_id, session)
    except Exception as e:
        session = get_session(session_id)
        if session:
            session["state"]["status"] = "failed"
            session["state"]["errors"].append(f"Graph execution error: {e}")
            set_session(session_id, session)

    session = get_session(session_id)
    return session["state"].get("status", "failed") if session else "failed"


async def generate_single_day(course_id: str, day_number: int) -> bool:
    """Generate notes for one day. Returns True on success."""
    course = get_course(course_id)
    if not course or not course.get("plan"):
        return False

    plan: CoursePlan = course["plan"]
    day = next((d for d in plan.days if d.day == day_number), None)
    if not day:
        return False

    session_id = generate_session_id()
    initial = _build_day_initial_state(day, course, session_id)
    create_session(session_id, initial, auto_approve_tutor=True)

    course.setdefault("day_sessions", {})[str(day_number)] = session_id
    course["current_generating_day"] = day_number
    course["current_day_title"] = day.title
    course["current_session_id"] = session_id
    set_course(course_id, course)

    status = await run_day_graph(session_id, initial)
    session = get_session(session_id)

    if status == "completed" and session:
        outputs = session["state"].get("output_files", [])
        course = get_course(course_id)
        if course:
            completed = list(course.get("days_completed", []))
            if day_number not in completed:
                completed.append(day_number)
            course["days_completed"] = sorted(completed)
            course.setdefault("day_outputs", {})[str(day_number)] = outputs
            course["next_day"] = day_number + 1
            course["current_generating_day"] = None
            course["current_day_title"] = None
            course["current_session_id"] = None
            set_course(course_id, course)
        return True

    course = get_course(course_id)
    if course:
        errs = list(course.get("errors", []))
        errs.append(f"Day {day_number} failed with status: {status}")
        course["errors"] = errs
        course["status"] = "failed"
        course["current_generating_day"] = None
        course["current_session_id"] = None
        set_course(course_id, course)
    return False


def _checkpoint_message(course: dict, through_day: int) -> str:
    start = through_day - course["checkpoint_every"] + 1
    return (
        f"Please review generated notes for days {start}–{through_day} in:\n"
        f"{course['output_root']}\n\n"
        "Approve to continue generating the next batch, or reject to stop."
    )


async def run_course_batch(course_id: str) -> None:
    """Generate days until next checkpoint or course completion."""
    course = get_course(course_id)
    if not course or course.get("status") not in ("generating",):
        return

    plan: CoursePlan = course["plan"]
    checkpoint_every = course.get("checkpoint_every", 4)
    next_day = course.get("next_day", 1)

    while next_day <= plan.total_days:
        course = get_course(course_id)
        if not course or course.get("status") != "generating":
            return

        ok = await generate_single_day(course_id, next_day)
        if not ok:
            return

        course = get_course(course_id)
        next_day = course.get("next_day", next_day + 1)

        if next_day > plan.total_days:
            course["status"] = "completed"
            course["checkpoint_message"] = None
            course["current_generating_day"] = None
            course["current_session_id"] = None
            set_course(course_id, course)
            logger.info(f"[course_runner] course completed | id={course_id}")
            return

        completed_day = next_day - 1
        if completed_day % checkpoint_every == 0:
            course["status"] = "awaiting_checkpoint"
            course["checkpoint_message"] = _checkpoint_message(course, completed_day)
            course["current_generating_day"] = None
            course["current_session_id"] = None
            set_course(course_id, course)
            logger.info(
                f"[course_runner] checkpoint pause after day {completed_day} | id={course_id}"
            )
            return
