from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..models import Project
from ..schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    principal: Principal = Depends(current_customer), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Project).where(Project.customer_id == principal.id).order_by(Project.created_at.desc())
    ).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    project = Project(customer_id=principal.id, name=payload.name, meta=payload.meta)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None or project.customer_id != principal.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
