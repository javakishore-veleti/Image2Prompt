"""A pydantic-settings source that hydrates settings from the CAF secret store.

When ``CAF_SECRET_PROVIDER`` is a cloud provider (aws/azure/gcp), this source
asks the ``img2pmpt-caf-secret`` client for each settings field (by its uppercase
env name) and feeds the values into ``ServiceSettings`` — so services read the
same fields whether the value came from the local ``.env`` or a cloud secret
store, with zero per-service code changes.

Fully lazy and fail-safe: if the provider is ``env``, the CAF lib isn't
installed, or a lookup fails, this returns ``{}`` and normal env/.env loading
applies.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

log = logging.getLogger(__name__)


class CafSecretsSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Values are provided in bulk via __call__; nothing per-field here.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        provider = (os.environ.get("CAF_SECRET_PROVIDER") or "env").lower()
        if provider == "env":
            return {}  # local/default path: plain env + .env already cover it
        try:
            from img2pmpt_caf_secret import GetSecretsReq, get_secret_client
        except Exception:
            return {}  # CAF lib not installed -> no-op

        try:
            client = get_secret_client()
            field_names = list(self.settings_cls.model_fields.keys())
            key_to_field = {name.upper(): name for name in field_names}
            resp = client.get_secrets_by_keys(GetSecretsReq(keys=list(key_to_field.keys())))
            if not resp.success:
                log.warning("CAF secrets unavailable (%s): %s", resp.error_code, resp.error_message)
                return {}
            return {
                key_to_field[k]: v
                for k, v in resp.values.items()
                if v is not None and k in key_to_field
            }
        except Exception as exc:  # never break settings construction
            log.warning("CAF secrets source error, ignoring: %s", exc)
            return {}
