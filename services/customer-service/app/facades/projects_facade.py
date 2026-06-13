from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.project_dao import ProjectDao
from ..dtos.internal_dtos import (
    CreateProjectReq,
    GetProjectReq,
    ListProjectsReq,
    ProjectListResp,
    ProjectResp,
)
from .interfaces import IProjectsFacade


class ProjectsFacade(BaseFacade, IProjectsFacade):
    def __init__(self, *, project_dao: ProjectDao) -> None:
        super().__init__()
        self.project_dao = project_dao

    @observe("ProjectsFacade.list_projects")
    def list_projects(self, req: ListProjectsReq) -> ProjectListResp:
        return self.project_dao.list(req)

    @observe("ProjectsFacade.create_project")
    def create_project(self, req: CreateProjectReq) -> ProjectResp:
        resp = self.project_dao.create(req)
        req.db.commit()
        return resp

    @observe("ProjectsFacade.get_project")
    def get_project(self, req: GetProjectReq) -> ProjectResp:
        return self.project_dao.get(req)
