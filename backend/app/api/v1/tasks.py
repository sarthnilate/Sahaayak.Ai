from datetime import datetime
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.models.all_models import Incident, Task
from backend.app.schemas.all_schemas import TaskCreate, TaskResponse, TaskUpdate
from backend.app.services.audit.service import audit_service
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class ApproveTaskRequest(BaseModel):
    approved_by: Optional[str] = "coordinator@sahaayak.ai"
    assigned_to: Optional[str] = None


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    incident_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Task).order_by(Task.created_at.desc())
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if incident_id:
        query = query.filter(Task.incident_id == incident_id)
    return query.all()


@router.post("/incidents/{incident_id}/tasks", response_model=TaskResponse)
def create_task(incident_id: str, payload: TaskCreate, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    task = Task(
        incident_id=incident_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        assigned_to=payload.assigned_to,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    audit_service.log(
        db=db,
        actor="coordinator",
        action="TASK_CREATED",
        entity_type="task",
        entity_id=task.id,
        details={"title": task.title, "priority": task.priority, "status": task.status},
    )

    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    before_status = task.status
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status
    if payload.assigned_to is not None:
        task.assigned_to = payload.assigned_to
    if payload.approved_by is not None:
        task.approved_by = payload.approved_by
        task.approved_at = datetime.utcnow()

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    audit_service.log(
        db=db,
        actor=payload.approved_by or "coordinator",
        action="TASK_STATUS_TRANSITION",
        entity_type="task",
        entity_id=task.id,
        details={"before": before_status, "after": task.status, "assigned_to": task.assigned_to},
    )

    return task


@router.post("/tasks/{task_id}/approve", response_model=TaskResponse)
def approve_task(task_id: str, payload: ApproveTaskRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "pending"
    task.approved_by = payload.approved_by or "coordinator@sahaayak.ai"
    task.approved_at = datetime.utcnow()
    if payload.assigned_to:
        task.assigned_to = payload.assigned_to

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    audit_service.log(
        db=db,
        actor=task.approved_by,
        action="TASK_APPROVED",
        entity_type="task",
        entity_id=task.id,
        details={"title": task.title, "assigned_to": task.assigned_to},
    )

    return task
