from __future__ import annotations

import base64

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe, set_span_attributes

from ..dao.proc_req_dao import ProcReqDao
from ..dao.prompt_dao import PromptDao
from ..dtos.internal_dtos import (
    CreateProcReqReq,
    DispatchReq,
    EnabledProvidersResp,
    GetRequestReq,
    ListEnabledProvidersReq,
    ListPromptsReq,
    ListRequestsReq,
    ProcessImageReq,
    ProcReqListResp,
    ProcReqResp,
    PromptListResp,
    ResolveProvidersReq,
    StoreImageReq,
)
from ..services.ai_dispatch_service import AiDispatchService
from ..services.provider_resolution_service import ProviderResolutionService
from ..services.storage_service import StorageService
from .interfaces import IImageFacade


class ImageFacade(BaseFacade, IImageFacade):
    """Orchestrates the upload -> store -> resolve -> fan-out -> persist flow."""

    def __init__(
        self,
        *,
        resolution_service: ProviderResolutionService,
        storage_service: StorageService,
        dispatch_service: AiDispatchService,
        proc_req_dao: ProcReqDao,
        prompt_dao: PromptDao,
    ) -> None:
        super().__init__()
        self.resolution_service = resolution_service
        self.storage_service = storage_service
        self.dispatch_service = dispatch_service
        self.proc_req_dao = proc_req_dao
        self.prompt_dao = prompt_dao

    @observe("ImageFacade.process_image", metric="image.generate")
    async def process_image(self, req: ProcessImageReq) -> ProcReqResp:
        set_span_attributes({"customer.id": req.customer_id})

        resolution = await self.resolution_service.resolve(
            ResolveProvidersReq(customer_id=req.customer_id, requested_providers=req.requested_providers)
        )
        if not resolution.selected:
            return ProcReqResp.failure(
                error_code="no_providers",
                error_message="No enabled providers available for this request.",
            )

        # 1) store image (storage failures are surfaced, not raised)
        try:
            stored = self.storage_service.store(
                StoreImageReq(
                    db=req.db,
                    customer_id=req.customer_id,
                    data=req.image_bytes,
                    content_type=req.content_type,
                    filename=req.filename,
                    storage_backend=resolution.storage_backend,
                )
            )
        except Exception as exc:
            self.log.warning("storage failed (%s): %s", resolution.storage_backend, exc)
            return ProcReqResp.failure(
                error_code="internal", error_message=f"Storage backend error: {exc}"
            )
        file_ref = stored.file_ref

        # 2) create request + pending provider rows
        created = self.proc_req_dao.create(
            CreateProcReqReq(
                db=req.db,
                customer_id=req.customer_id,
                project_id=req.project_id,
                file_ref_id=file_ref.id,
                instruction=req.instruction,
                selected_providers=resolution.selected,
                provider_id_map=resolution.provider_id_map,
                meta={
                    "content_type": req.content_type,
                    "filename": req.filename,
                    "size": len(req.image_bytes),
                },
            )
        )
        proc = created.request

        # 3) fan out to each provider
        image_b64 = base64.b64encode(req.image_bytes).decode("utf-8")
        media_type = req.content_type or "image/png"
        any_success = False
        for row in proc.providers:
            dispatch = await self.dispatch_service.invoke(
                DispatchReq(
                    provider_key=row.provider_key,
                    request_id=proc.id,
                    instruction=req.instruction,
                    image_base64=image_b64,
                    media_type=media_type,
                    config=resolution.config_map.get(row.provider_key, {}),
                )
            )
            payload = dispatch.payload
            row.response_payload = payload
            row.latency_ms = payload.get("latency_ms")
            if payload.get("status") == "success":
                row.status = "success"
                row.output_text = payload.get("output_text")
                any_success = True
            else:
                row.status = "error"
                row.error = payload.get("error")

        proc.status = "completed" if any_success else "failed"
        req.db.commit()
        req.db.refresh(proc)
        Metrics.counter_add("image.generate", 1, {"status": proc.status})
        self.log.info("process_image done request_id=%s status=%s", proc.id, proc.status)
        return ProcReqResp(request=proc)

    @observe("ImageFacade.list_requests")
    def list_requests(self, req: ListRequestsReq) -> ProcReqListResp:
        return self.proc_req_dao.list(req)

    @observe("ImageFacade.get_request")
    def get_request(self, req: GetRequestReq) -> ProcReqResp:
        return self.proc_req_dao.get(req)

    @observe("ImageFacade.list_prompts")
    def list_prompts(self, req: ListPromptsReq) -> PromptListResp:
        return self.prompt_dao.list(req)

    @observe("ImageFacade.list_providers")
    async def list_providers(self, req: ListEnabledProvidersReq) -> EnabledProvidersResp:
        return await self.resolution_service.list_enabled(req)
