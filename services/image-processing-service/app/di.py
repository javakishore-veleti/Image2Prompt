"""DI container for image-processing-service."""

from __future__ import annotations

from .dao.file_ref_dao import FileRefDao
from .dao.proc_req_dao import ProcReqDao
from .dao.prompt_dao import PromptDao
from .dao.stats_dao import StatsDao
from .facades.image_facade import ImageFacade
from .facades.interfaces import IImageFacade
from .services.ai_dispatch_service import AiDispatchService
from .services.provider_resolution_service import ProviderResolutionService
from .services.storage_service import StorageService

# DAOs
_file_ref_dao = FileRefDao()
_proc_req_dao = ProcReqDao()
_prompt_dao = PromptDao()
_stats_dao = StatsDao()

# Services
_resolution_service = ProviderResolutionService()
_storage_service = StorageService(file_ref_dao=_file_ref_dao)
_dispatch_service = AiDispatchService()

# Facade
_image_facade: IImageFacade = ImageFacade(
    resolution_service=_resolution_service,
    storage_service=_storage_service,
    dispatch_service=_dispatch_service,
    proc_req_dao=_proc_req_dao,
    prompt_dao=_prompt_dao,
    stats_dao=_stats_dao,
)


def get_image_facade() -> IImageFacade:
    return _image_facade
