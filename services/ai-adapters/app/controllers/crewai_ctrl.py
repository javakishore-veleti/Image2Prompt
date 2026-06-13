"""CrewAI provider (real) — a single multimodal agent + task in a Crew, running
on a Bedrock LLM. The image is written to a temp file the multimodal agent reads.
SDK imported lazily; blocking kickoff offloaded to a thread."""

from __future__ import annotations

import base64
import os
import tempfile

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController

_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/webp": ".webp"}


class CrewAIController(ProviderController):
    key = "crewai"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from crewai import LLM, Agent, Crew, Task

        suffix = _EXT.get((req.media_type or "image/png").lower(), ".png")
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(base64.b64decode(req.image_base64))

            llm = LLM(model=f"bedrock/{req.config.get('model_id', self.model_id)}")
            agent = Agent(
                role="Reverse Prompt Engineer",
                goal="Produce a text-to-image prompt that could recreate a given image",
                backstory="You analyze images and articulate the prompt that would generate them.",
                multimodal=True,
                llm=llm,
                verbose=False,
            )
            task = Task(
                description=f"{req.instruction}\nImage file: {path}",
                expected_output="A single, detailed text-to-image prompt.",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            return str(result).strip(), {"provider": "crewai"}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
