from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class ImageSettings(ServiceSettings):
    service_name: str = "image-processing-service"
    db_schema: str = "img2pmpt_image"


settings = ImageSettings()
