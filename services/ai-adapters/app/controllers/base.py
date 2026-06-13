from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvokeResult:
    output_text: str
    raw: dict[str, Any] = field(default_factory=dict)


class ProviderController(ABC):
    """Base class for a provider controller.

    Each provider (Bedrock, Anthropic, OpenAI, ...) implements ``invoke`` to turn
    an image + instruction into a generated text prompt. ``implemented`` lets the
    registry advertise which providers are live vs. registered stubs.
    """

    key: str = "abstract"
    implemented: bool = False

    @abstractmethod
    async def invoke(
        self, *, request_id: str, instruction: str, image_base64: str, media_type: str, config: dict
    ) -> InvokeResult:
        ...
