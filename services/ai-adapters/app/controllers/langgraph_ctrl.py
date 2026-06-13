"""LangGraph provider (real) — a small two-node graph (draft -> refine) over a
Bedrock chat model. Demonstrates genuine graph orchestration rather than a single
call. SDKs imported lazily; the blocking run is offloaded to a thread."""

from __future__ import annotations

import base64

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class LangGraphController(ProviderController):
    key = "langgraph"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from langchain_aws import ChatBedrockConverse
        from langchain_core.messages import HumanMessage, SystemMessage
        from langgraph.graph import END, START, StateGraph
        from typing_extensions import TypedDict

        b64 = req.image_base64
        mime = req.media_type or "image/png"
        llm = ChatBedrockConverse(
            model=req.config.get("model_id", self.model_id),
            region_name=req.config.get("region", self.region),
        )

        class State(TypedDict):
            draft: str
            final: str

        def draft(state: State) -> dict:
            msg = HumanMessage(
                content=[
                    {"type": "text", "text": req.instruction},
                    {"type": "image", "source_type": "base64", "mime_type": mime, "data": b64},
                ]
            )
            return {"draft": llm.invoke([msg]).text()}

        def refine(state: State) -> dict:
            msg = [
                SystemMessage(content="Tighten this text-to-image prompt; keep it one vivid paragraph."),
                HumanMessage(content=state["draft"]),
            ]
            return {"final": llm.invoke(msg).text()}

        graph = StateGraph(State)
        graph.add_node("draft", draft)
        graph.add_node("refine", refine)
        graph.add_edge(START, "draft")
        graph.add_edge("draft", "refine")
        graph.add_edge("refine", END)
        app = graph.compile()
        result = app.invoke({"draft": "", "final": ""})
        text = (result.get("final") or result.get("draft") or "").strip()
        return text, {"provider": "langgraph", "nodes": ["draft", "refine"]}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
