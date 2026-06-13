"""Maps a failed ``*Resp`` (error_code) to an HTTP error at the controller edge.

Layers never raise HTTP errors; they return ``BaseResp`` with ``success=False``
and an ``error_code``. Controllers call ``ensure_ok(resp)`` to translate.
"""

from __future__ import annotations

from fastapi import HTTPException

ERROR_STATUS: dict[str, int] = {
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
    "conflict": 409,
    "no_providers": 400,
    "not_configured": 400,
    "unprocessable": 422,
    "locked": 423,  # account temporarily locked (too many failed sign-ins)
    "upstream_error": 502,
    "internal": 500,
}


def ensure_ok(resp):
    """Raise HTTPException if ``resp`` failed; otherwise return it unchanged."""
    if getattr(resp, "success", True):
        return resp
    code = getattr(resp, "error_code", None) or "internal"
    status = ERROR_STATUS.get(code, 500)
    raise HTTPException(status_code=status, detail=getattr(resp, "error_message", code))
