"""Style Coach (spec §3.6). RAG context + prompt-cached preamble + SSE streaming."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db, SessionLocal
from ...deps import get_current_user
from ...config import get_settings
from ...models import User, CoachConversation, CoachMessage
from ...core import llm
from .service import build_context_preamble, COACH_FALLBACK

router = APIRouter(prefix="/v1/coach", tags=["coach"])
settings = get_settings()


def _owned_convo(db: Session, user: User, cid: str) -> CoachConversation:
    try:
        c = db.get(CoachConversation, uuid.UUID(cid))
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if not c or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return c


@router.post("/conversations", status_code=201)
def new_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    convo = CoachConversation(user_id=user.id)
    db.add(convo); db.commit(); db.refresh(convo)
    return {"conversation_id": str(convo.id)}


@router.get("/conversations/{cid}")
def history(cid: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    convo = _owned_convo(db, user, cid)
    msgs = list(db.scalars(select(CoachMessage).where(
        CoachMessage.conversation_id == convo.id).order_by(CoachMessage.created_at)))
    return {"conversation_id": cid,
            "messages": [{"role": m.role, "content": m.content} for m in msgs]}


@router.post("/conversations/{cid}/messages")
def send(cid: str, payload: dict, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    """Non-streaming reply (simple clients). SSE variant below for token streaming."""
    convo = _owned_convo(db, user, cid)
    text = (payload.get("message") or "").strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty message")

    db.add(CoachMessage(conversation_id=convo.id, role="user", content=text))
    db.commit()

    system = build_context_preamble(db, user.id)
    prior = _prior_turns(db, convo.id)
    reply = llm.complete(system, prior + [{"role": "user", "content": text}],
                         model=llm.model_for('coach'), max_tokens=600, fallback=COACH_FALLBACK)

    db.add(CoachMessage(conversation_id=convo.id, role="assistant", content=reply))
    db.commit()
    return {"conversation_id": cid, "reply": reply}


@router.post("/conversations/{cid}/messages/stream")
def send_stream(cid: str, payload: dict, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """SSE token stream. The preamble is prompt-cached so multi-turn chat is cheap."""
    convo = _owned_convo(db, user, cid)
    text = (payload.get("message") or "").strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty message")

    db.add(CoachMessage(conversation_id=convo.id, role="user", content=text))
    db.commit()
    system = build_context_preamble(db, user.id)
    prior = _prior_turns(db, convo.id)
    convo_id = convo.id

    def event_stream():
        collected = []
        for chunk in llm.stream(system, prior + [{"role": "user", "content": text}],
                                model=llm.model_for('coach'), max_tokens=600,
                                fallback=COACH_FALLBACK):
            collected.append(chunk)
            yield f"data: {chunk}\n\n"
        # persist the full assistant turn once the stream completes
        full = "".join(collected)
        s = SessionLocal()
        try:
            s.add(CoachMessage(conversation_id=convo_id, role="assistant", content=full))
            s.commit()
        finally:
            s.close()
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _prior_turns(db: Session, convo_id, limit: int = 10) -> list[dict]:
    msgs = list(db.scalars(select(CoachMessage).where(
        CoachMessage.conversation_id == convo_id)
        .order_by(CoachMessage.created_at.desc()).limit(limit)))
    msgs.reverse()
    # exclude the just-added current user message (it's appended by the caller)
    return [{"role": m.role, "content": m.content} for m in msgs[:-1]]
