"""Core orchestration: store the image, resolve providers, fan out, persist.

Provider selection cascade (most specific wins):
  per-request override  ->  customer default preferences  ->  all admin-enabled.
Only globally-enabled providers are ever dispatched.
"""

from __future__ import annotations

import base64
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from image2prompt_shared.http_client import get_json, post_json
from image2prompt_shared.storage import get_storage_backend

from .config import settings
from .models import FileRef, ProcReqLog, ProcReqLogProvider


async def _fetch_enabled_providers() -> list[dict]:
    url = f"{settings.admin_service_url}/internal/providers"
    return await get_json(url, params={"enabled": "true"})


async def _fetch_customer_prefs(customer_id: str) -> dict:
    url = f"{settings.customer_service_url}/internal/customers/{customer_id}/preferences"
    return await get_json(url)


def _resolve_selection(
    *, requested: list[str] | None, default_keys: list[str], enabled_map: dict[str, str]
) -> list[str]:
    if requested:
        candidate = requested
    elif default_keys:
        candidate = default_keys
    else:
        candidate = list(enabled_map.keys())
    # Only enabled providers may run.
    selected = [k for k in candidate if k in enabled_map]
    return selected


def _store_image(
    *, customer_id: str, data: bytes, content_type: str, storage_backend: str, filename: str
) -> FileRef:
    backend = get_storage_backend(storage_backend, base_dir=settings.local_storage_dir)
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "bin")[:10]
    key = f"{customer_id}/{uuid.uuid4()}.{ext}"
    stored = backend.save(data, key=key, content_type=content_type)
    return FileRef(
        customer_id=customer_id,
        backend=stored.backend,
        location=stored.location,
        content_type=stored.content_type,
        size=stored.size,
        meta={"original_filename": filename},
    )


async def process_image(
    db: Session,
    *,
    customer_id: str,
    image_bytes: bytes,
    content_type: str,
    filename: str,
    instruction: str,
    project_id: str | None = None,
    requested_providers: list[str] | None = None,
) -> ProcReqLog:
    prefs = await _fetch_customer_prefs(customer_id)
    enabled = await _fetch_enabled_providers()
    enabled_map = {p["key"]: p["id"] for p in enabled}
    config_map = {p["key"]: p.get("config", {}) for p in enabled}

    storage_backend = prefs.get("storage_backend", "local")
    default_keys = prefs.get("default_provider_keys", []) or []

    selected = _resolve_selection(
        requested=requested_providers, default_keys=default_keys, enabled_map=enabled_map
    )
    if not selected:
        raise HTTPException(
            status_code=400,
            detail="No enabled providers available for this request. "
            "Ask an admin to enable a provider or adjust your preferences.",
        )

    # 1) Store the image.
    file_ref = _store_image(
        customer_id=customer_id,
        data=image_bytes,
        content_type=content_type,
        storage_backend=storage_backend,
        filename=filename,
    )
    db.add(file_ref)
    db.flush()

    # 2) Create the request log.
    req = ProcReqLog(
        customer_id=customer_id,
        project_id=project_id,
        file_ref_id=file_ref.id,
        instruction=instruction,
        status="processing",
        requested_providers=selected,
        meta={"content_type": content_type, "filename": filename, "size": len(image_bytes)},
    )
    db.add(req)
    db.flush()

    # 3) Fan out to each selected provider.
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    media_type = content_type or "image/png"
    any_success = False
    for key in selected:
        row = ProcReqLogProvider(
            proc_req_id=req.id,
            provider_key=key,
            provider_id=enabled_map.get(key),
            status="pending",
            request_payload={"instruction": instruction, "provider_key": key},
        )
        db.add(row)
        db.flush()
        try:
            resp = await post_json(
                f"{settings.ai_adapters_url}/invoke",
                json={
                    "provider_key": key,
                    "request_id": req.id,
                    "instruction": instruction,
                    "image_base64": image_b64,
                    "media_type": media_type,
                    "config": config_map.get(key, {}),
                },
            )
            row.response_payload = resp
            row.latency_ms = resp.get("latency_ms")
            if resp.get("status") == "success":
                row.status = "success"
                row.output_text = resp.get("output_text")
                any_success = True
            else:
                row.status = "error"
                row.error = resp.get("error")
        except Exception as exc:  # network/transport failure calling ai-adapters
            row.status = "error"
            row.error = {"type": exc.__class__.__name__, "message": str(exc)}

    req.status = "completed" if any_success else "failed"
    db.commit()
    db.refresh(req)
    return req
