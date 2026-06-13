from __future__ import annotations

import json

from image2prompt_shared.crypto import TokenCipher
from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..dao.audit_dao import AuditDao
from ..dao.provider_dao import ProviderDao
from ..dtos.internal_dtos import (
    CreateProviderReq,
    GetProviderReq,
    ListProvidersReq,
    ProviderListResp,
    ProviderResp,
    RecordAuditReq,
    UpdateProviderReq,
)
from ..masking import MASK, merge_with_existing
from ..models import Provider
from .interfaces import IProvidersFacade


class ProvidersFacade(BaseFacade, IProvidersFacade):
    def __init__(self, *, provider_dao: ProviderDao, audit_dao: AuditDao) -> None:
        super().__init__()
        self.provider_dao = provider_dao
        self.audit_dao = audit_dao
        # Encrypts provider config (API keys/secrets) at rest. No-op if no key set.
        # Previous keys enable safe rotation (decrypt falls back to them).
        prev = [k.strip() for k in (settings.token_encryption_key_previous or "").split(",") if k.strip()]
        self.cipher = TokenCipher(settings.token_encryption_key, previous_keys=prev)

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
        config_keys = list((req.config or {}).keys())
        req.config = self._seal_config(req.config)
        resp = self.provider_dao.create(req)
        if resp.success:
            self._audit(req, "provider.create", req.key, {"enabled": req.enabled, "config_keys": config_keys})
            req.db.commit()
            self._decrypt_for_response(req.db, resp.provider)
        return resp

    @observe("ProvidersFacade.update_provider")
    def update_provider(self, req: UpdateProviderReq) -> ProviderResp:
        detail: dict = {}
        if req.enabled is not None:
            detail["enabled"] = req.enabled
        if req.name is not None:
            detail["name"] = req.name
        if req.config is not None:
            incoming = req.config
            # Record only key NAMES — never secret values.
            detail["config_set"] = [k for k, v in incoming.items() if v is not None and v != MASK]
            detail["config_removed"] = [k for k, v in incoming.items() if v is None]
            # Restore any masked (unchanged) secrets from the stored config, then
            # re-seal the merged result before persisting.
            current = self.provider_dao.get(GetProviderReq(db=req.db, provider_id=req.provider_id))
            existing = self._open_config(current.provider.config) if current.success else {}
            req.config = self._seal_config(merge_with_existing(incoming, existing))
        resp = self.provider_dao.update(req)
        if resp.success:
            self._audit(req, "provider.update", resp.provider.key, detail)
            req.db.commit()
            self._decrypt_for_response(req.db, resp.provider)
        return resp

    def _audit(self, req, action: str, target: str, detail: dict) -> None:
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action=action, target=target, detail=detail,
                actor_id=getattr(req, "actor_id", None), actor_email=getattr(req, "actor_email", None),
            )
        )

    def reencrypt_configs(self, db: Session) -> int:
        """Re-seal every provider's config under the current key. Used after a key
        rotation (decrypt falls back to previous keys). No-op if encryption off."""
        if not self.cipher.enabled:
            return 0
        changed = 0
        for provider in db.scalars(select(Provider)):
            cfg = provider.config or {}
            if not cfg.get("_enc"):
                continue
            opened = self._open_config(cfg)
            resealed = self._seal_config(opened)
            if resealed != cfg:
                provider.config = resealed
                changed += 1
        if changed:
            db.commit()
        self.log.info("re-encrypted config for %d provider(s)", changed)
        return changed

    def rotation_status(self, db: Session) -> tuple[int, int]:
        """(encrypted configs, of those not under the current key)."""
        if not self.cipher.enabled:
            return (0, 0)
        total = stale = 0
        for provider in db.scalars(select(Provider)):
            blob = (provider.config or {}).get("_enc")
            if not blob or not TokenCipher.is_encrypted(blob):
                continue
            total += 1
            if not self.cipher.is_current(blob):
                stale += 1
        return (total, stale)

    def _decrypt_for_response(self, db: Session, provider: Provider | None) -> None:
        if provider is None:
            return
        # After commit, attributes are expired; reload them all, then swap config
        # for its plaintext. No subsequent commit => the plaintext isn't persisted.
        db.refresh(provider)
        provider.config = self._open_config(provider.config or {})
