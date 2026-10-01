"""Authenticated HTTP boundary. Blocking SQLite/adapter work uses FastAPI's pool."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header
from pydantic import Field
from starlette.concurrency import run_in_threadpool
from core.governor_identity import get_principal, require
from core.governor_policy import Strict
from core.governor_store import Store
from core.governor_adapters import Adapters
from core.governor_service import Governor

BASE = Path(__file__).resolve().parent.parent
store = Store(BASE / "data/governor.db")
governor = Governor(store, Adapters(store, BASE / "data/demo_sales.db", BASE / "data/reports"))
router = APIRouter(prefix="/api", tags=["PNG5 Governor"])


async def body(request):
    data = await request.body()
    try:
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result
        raw = json.loads(data, object_pairs_hook=unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(raw, dict):
            raise ValueError()
        stack, count = [(raw, 0)], 0
        while stack:
            value, depth = stack.pop()
            count += 1
            if depth > 12 or count > 512 or (isinstance(value, str) and len(value) > 8000):
                raise ValueError("JSON structural limit")
            if isinstance(value, dict):
                stack.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value)
        return raw
    except (ValueError, UnicodeDecodeError, RecursionError):
        # Invalid authenticated action still flows through the durable denial path.
        return {"invalid_json": True}


@router.post("/authorize")
async def authorize(request: Request, principal=Depends(get_principal)):
    return await run_in_threadpool(governor.submit, await body(request), principal, None, True)


@router.post("/actions")
async def execute(request: Request, principal=Depends(get_principal), idempotency_key: Optional[str] = Header(default=None)):
    return await run_in_threadpool(governor.submit, await body(request), principal, idempotency_key)


@router.get("/actions/{request_id}")
def action_status(request_id: str, principal=Depends(get_principal)):
    return governor.status(request_id, principal)


@router.post("/actions/{request_id}/cancel")
def cancel(request_id: str, principal=Depends(get_principal)):
    return governor.cancel(request_id, principal)


@router.get("/reviews")
def reviews(principal=Depends(get_principal), limit: int = Query(50, ge=1, le=100)):
    require(principal, "review")
    return {"reviews": governor.list_reviews(principal, limit)}


@router.get("/reviews/{request_id}")
def review_details(request_id: str, principal=Depends(get_principal)):
    return governor.status(request_id, principal, True)


class ReviewBody(Strict):
    comment: str = Field(default="", max_length=500)


@router.post("/reviews/{request_id}/approve")
def approve(request_id: str, payload: ReviewBody, principal=Depends(get_principal)):
    return governor.review(request_id, principal, "APPROVED", payload.comment)


@router.post("/reviews/{request_id}/reject")
def reject(request_id: str, payload: ReviewBody, principal=Depends(get_principal)):
    return governor.review(request_id, principal, "REJECTED", payload.comment)


@router.get("/audit")
def audit(principal=Depends(get_principal), limit: int = Query(50, ge=1, le=100)):
    with store.connection() as c:
        if "audit" in principal.permissions:
            rows = c.execute("SELECT event_json,previous_hash,event_hash FROM audit_events ORDER BY sequence DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = c.execute("SELECT event_json,previous_hash,event_hash FROM audit_events WHERE json_extract(event_json,'$.principal_id')=? ORDER BY sequence DESC LIMIT ?", (principal.principal_id, limit)).fetchall()
    return {"events": [{**json.loads(r[0]), "previous_hash": r[1], "event_hash": r[2]} for r in rows]}


@router.get("/audit/verify")
def verify(principal=Depends(get_principal)):
    require(principal, "audit")
    return store.verify()


@router.get("/audit/checkpoint")
def checkpoint(principal=Depends(get_principal)):
    require(principal, "audit")
    result = store.verify()
    if not result["valid"]:
        raise HTTPException(409, "Audit chain invalid")
    return {k: result[k] for k in ("event_count", "head_hash")}


class Checkpoint(Strict):
    event_count: int = Field(ge=0)
    head_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.post("/audit/verify")
def compare_checkpoint(payload: Checkpoint, principal=Depends(get_principal)):
    require(principal, "audit")
    return store.verify(payload.model_dump())


@router.get("/metrics")
def metrics(principal=Depends(get_principal)):
    require(principal, "audit")
    with store.connection() as c:
        return {"states": dict(c.execute("SELECT state,count(*) FROM actions GROUP BY state").fetchall())}


