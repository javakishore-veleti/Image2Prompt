"""LiteLLM — one interface over many providers. The model prefix selects the
backend; LiteLLM reads that provider's key from env. SDK imported lazily."""

from __future__ import annotations

from ..client.dtos import RouteReq, RouteResp
from ..config import CafRoutersSettings
from .interfaces import IRouterProvider, data_uri


class LiteLLMProvider(IRouterProvider):
    name = "litellm"

    def __init__(self, settings: CafRoutersSettings) -> None:
        self._model = settings.litellm_model

    def route(self, req: RouteReq) -> RouteResp:
        try:
            import litellm

            model = req.model or self._model
            resp = litellm.completion(
                model=model,
                max_tokens=req.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": req.instruction},
                            {"type": "image_url", "image_url": {"url": data_uri(req.media_type, req.image_base64)}},
                        ],
                    }
                ],
            )
            content = resp["choices"][0]["message"]["content"]
            return RouteResp(router=self.name, model=model, output_text=(content or "").strip())
        except Exception as exc:
            return RouteResp(success=False, router=self.name, error_code="provider_error", error_message=str(exc))
