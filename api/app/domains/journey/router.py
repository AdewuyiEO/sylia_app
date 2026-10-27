"""Style journey: streak, freezes, weekly challenge, level and badges."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User
from ..daily_look.service import local_today
from . import service

router = APIRouter(prefix="/v1/journey", tags=["journey"])


@router.get("")
def journey(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.refresh(db, user, local_today(user))


@router.post("/challenge/accept")
def accept(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = local_today(user)
    try:
        service.accept_challenge(db, user, today)
    except ValueError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add a few more pieces to unlock weekly challenges")
    return service.refresh(db, user, today)
