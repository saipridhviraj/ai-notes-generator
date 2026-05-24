"""Thin async client for the AI Notes Generator Railway API."""
import os
import httpx

API_URL = os.getenv("RAILWAY_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("APP_API_KEY", "")
_HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def start_generation(topic: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API_URL}/generate", json={"topic": topic}, headers=_HEADERS)
        r.raise_for_status()
        return r.json()


async def get_status(session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API_URL}/status/{session_id}", headers=_HEADERS)
        r.raise_for_status()
        return r.json()


async def tutor_respond(session_id: str, approved: bool, feedback: str = "") -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{API_URL}/tutor/respond/{session_id}",
            json={"approved": approved, "feedback": feedback, "response_to": "plan_verification"},
            headers=_HEADERS,
        )
        r.raise_for_status()


async def get_result(session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API_URL}/result/{session_id}", headers=_HEADERS)
        r.raise_for_status()
        return r.json()
