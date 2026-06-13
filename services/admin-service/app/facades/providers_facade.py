from __future__ import annotations

import json

from image2prompt_shared.crypto import TokenCipher
from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe
from sqlalchemy.orm import Session

from ..config import settings
from ..dao.provider_dao import ProviderDao
from ..dtos.internal_dtos import (
    CreateProviderReq,
    GetProviderReq,
    ListProvidersReq,
    ProviderListResp,
    ProviderResp,
    UpdateProviderReq,
)
from ..masking import merge_with_existing
from ..models import Provider
from .interfaces import IProvidersFacade


class ProvidersFacade(BaseFacade, IProvidersFacade):
    def __init__(self, *, provider_dao: ProviderDao) -> None:
        super().__init__()
        self.provider_dao = provider_dao
        # Encrypts provider config (API keys/secrets) at rest. No-op if no key set.
        self.cipher = TokenCipher(settings.token_encryption_key)

    # --- config-at-rest helpers ----------------------------------------------
    def _seal_config(self, config: dict | None) -> dict:
        """Encrypt the whole config blob into ``{"_enc": "..."}``. Pass-through
        when there's nothing to encrypt or no key is configured."""
        if not config or not self.cipher.enabled:
            return config or {}
        return {"_enc": self.cipher.encrypt(json.dumps(config))}

    def _open_config(self, config: dict | None) -> dict:
        """Inverse of ``_seal_config``. Legacy plaintext configs pass through."""
        if not config:
            return config or {}
        blob = config.get("_enc")
        if not blob:
            return config  # legacy plaintext / unencrypted
        opened = self.cipher.decrypt(blob)
        if not opened:
            return {}  # key missing/rotated — degrade rather than leak ciphertext
        try:
            return json.loads(opened)
        except (ValueError, TypeError):
            return {}

    @observe("ProvidersFacade.list_providers")
    def list_providers(self, req: ListProvidersReq) -> ProviderListResp:
        resp = self.provider_dao.list(req)
        if resp.success:
            # Decrypt for the response. Safe: read path never commits and the
            # session has autoflush off, so the plaintext is never written back.
            for p in resp.providers:
                p.config = self._open_config(p.config or {})
        return resp

    @observe("ProvidersFacade.create_provider")
    def create_provider(self, req: CreateProviderReq) -> ProviderResp:
        req.config = self._seal_config(req.config)
        resp = self.provider_dao.create(req)
        if resp.success:
            req.db.commit()
            self._decrypt_for_response(req.db, resp.provider)
        return resp

    @observe("ProvidersFacade.update_provider")
    def update_provider(self, req: UpdateProviderReq) -> ProviderResp:
        if req.config is not None:
            # Restore any masked (unchanged) secrets from the stored config, then
            # re-seal the merged result before persisting.
            current = self.provider_dao.get(GetProviderReq(db=req.db, provider_id=req.provider_id))
            existing = self._open_config(current.provider.config) if current.success else {}
            req.config = self._seal_config(merge_with_existing(req.config, existing))
        resp = self.provider_dao.update(req)
        if resp.success:
            req.db.commit()
            self._decrypt_for_response(req.db, resp.provider)
        return resp

    def _decrypt_for_response(self, db: Session, provider: Provider | None) -> None:
        if provider is None:
            return
        # After commit, attributes are expired; reload them all, then swap config
        # for its plaintext. No subsequent commit => the plaintext isn't persisted.
        db.refresh(provider)
        provider.config = self._open_config(provider.config or {})
