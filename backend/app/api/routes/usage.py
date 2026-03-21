from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.rate_limit import get_usage_summary

router = APIRouter()


@router.get("")
def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return today's usage counts and daily limits for the current user."""
    return get_usage_summary(db, current_user.id)
