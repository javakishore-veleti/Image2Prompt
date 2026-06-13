"""OpenRouter — OpenAI-compatible router. Uses the openai SDK against OpenRouter's
base URL; vision via an image_url data URI. SDK imported lazily."""

from __future__ import annotations

from ..client.dtos import RouteReq, RouteResp
from ..config import CafRoutersSettings
from .interfaces import IRouterProvider, data_uri


class OpenRouterProvider(IRouterProvider):
    name = "openrouter"

    def __init__(self, settings: CafRoutersSettings) -> None:
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        self._base_url = settings.openrouter_base_url

    def route(self, req: RouteReq) -> RouteResp:
        if not self._api_key:
            return RouteResp(
                success=False, router=self.name, error_code="not_configured",
                error_message="OPENROUTER_API_KEY is not configured",
            )
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            model = req.model or self._model
            resp = client.chat.completions.create(
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
                extra_headers={"HTTP-Referer": "https://image2prompt.local", "X-Title": "Image2Prompt"},
            )
            return RouteResp(
                router=self.name, model=model,
                output_text=(resp.choices[0].message.content or "").strip(),
                raw={"id": getattr(resp, "id", None)},
            )
        except Exception as exc:
            return RouteResp(success=False, router=self.name, error_code="provider_error", error_message=str(exc))
