from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CreateProjectReq,
    GetProjectReq,
    ListProjectsReq,
    ProjectListResp,
    ProjectResp,
)
from ..models import Project


class ProjectDao(BaseDao):
    @observe("ProjectDao.list")
    def list(self, req: ListProjectsReq) -> ProjectListResp:
        rows = req.db.scalars(
            select(Project)
            .where(Project.customer_id == req.customer_id)
            .order_by(Project.created_at.desc())
        ).all()
        return ProjectListResp(projects=list(rows))

    @observe("ProjectDao.create")
    def create(self, req: CreateProjectReq) -> ProjectResp:
        project = Project(customer_id=req.customer_id, name=req.name, meta=req.meta)
        req.db.add(project)
        req.db.flush()
        return ProjectResp(project=project)

    @observe("ProjectDao.get")
    def get(self, req: GetProjectReq) -> ProjectResp:
        project = req.db.get(Project, req.project_id)
        if project is None or project.customer_id != req.customer_id:
            return ProjectResp.failure(error_code="not_found", error_message="Project not found")
        return ProjectResp(project=project)
