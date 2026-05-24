"""Internal API for VB Academy to catch up on missed note.ready events."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import require_api_key
from utils import note_event_outbox as outbox

router = APIRouter(prefix="/internal/note-events", tags=["internal"])


class NoteEventItem(BaseModel):
    event_id: str
    status: str
    attempts: int
    last_error: Optional[str] = None
    payload: dict


class NoteEventListResponse(BaseModel):
    count: int
    events: List[NoteEventItem]


@router.get("/pending", response_model=NoteEventListResponse, dependencies=[Depends(require_api_key)])
async def list_pending_note_events(limit: int = 100):
    """
    Return undelivered note.ready payloads for VB Academy catch-up indexing.
    Academy should index these, then rely on webhooks for new events.
    """
    limit = min(max(limit, 1), 500)
    rows = outbox.list_pending(limit=limit)
    return NoteEventListResponse(
        count=len(rows),
        events=[NoteEventItem(**{k: v for k, v in row.items() if k != "created_at" and k != "updated_at"}) for row in rows],
    )


@router.get("/{event_id}", response_model=NoteEventItem, dependencies=[Depends(require_api_key)])
async def get_note_event(event_id: str):
    row = outbox.get_event(event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return NoteEventItem(
        **{k: v for k, v in row.items() if k not in ("created_at", "updated_at")}
    )
