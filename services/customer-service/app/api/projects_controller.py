from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_projects_facade
from ..dtos.internal_dtos import CreateProjectReq, GetProjectReq, ListProjectsReq
from ..facades.interfaces import IProjectsFacade
from ..schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProjectsFacade = Depends(get_projects_facade),
):
    resp = ensure_ok(facade.list_projects(ListProjectsReq(db=db, customer_id=principal.id)))
    return resp.projects


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProjectsFacade = Depends(get_projects_facade),
):
    resp = ensure_ok(
        facade.create_project(
            CreateProjectReq(db=db, customer_id=principal.id, name=payload.name, meta=payload.meta)
        )
    )
    return resp.project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProjectsFacade = Depends(get_projects_facade),
):
    resp = ensure_ok(
        facade.get_project(GetProjectReq(db=db, customer_id=principal.id, project_id=project_id))
    )
    return resp.project
