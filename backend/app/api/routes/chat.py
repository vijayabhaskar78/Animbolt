from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.models.user import User

router = APIRouter()


class ChatMessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _verify_project(project_id: str, user_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/{project_id}/chat", response_model=list[ChatMessageResponse])
def get_chat(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageResponse]:
    _verify_project(project_id, current_user.id, db)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at)
        .all()
    )


@router.post("/{project_id}/chat", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def add_chat_message(
    project_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    _verify_project(project_id, current_user.id, db)
    msg = ChatMessage(project_id=project_id, role=payload.role, content=payload.content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
