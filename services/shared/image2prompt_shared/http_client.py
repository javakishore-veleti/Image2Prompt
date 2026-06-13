"""Thin async helper for service-to-service HTTP calls."""

from __future__ import annotations

from typing import Any

import httpx


async def get_json(
    url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float = 10.0
) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def post_json(
    url: str, *, json: dict, headers: dict | None = None, timeout: float = 60.0
) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=json, headers=headers)
        resp.raise_for_status()
        return resp.json()
