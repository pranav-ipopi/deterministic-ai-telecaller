"""
ALR Voice Agent — minimal multi-tenant dispatch API.

ONE endpoint: POST /dispatch
  - Auth: X-API-Key header (shared with ALR)
  - Body: the ALR lead JSON (exactly as today)
  - Action: look up tenant by customer_name in tenants.db, then call
    LiveKit's AgentDispatch API with all the metadata the agent needs.

That's it. LiveKit Cloud handles queueing, retries, scaling, and dispatch.
The agent posts results directly back to ALR (no relay through here).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from livekit import api
from pydantic import BaseModel

# ─── Config ────────────────────────────────────────────────────────────
LIVEKIT_URL        = os.environ["LIVEKIT_URL"]
LIVEKIT_API_KEY    = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]
SHARED_API_KEY     = os.environ["SHARED_API_KEY"]       # ALR <-> api auth
AGENT_API_KEY      = os.environ["AGENT_API_KEY"]        # agent <-> api auth (lookups + callbacks)
DB_PATH            = os.environ.get("DB_PATH", "tenants.db")
OUTBOUND_AGENT     = os.environ.get("OUTBOUND_AGENT", "outbound-caller")

# How long (days) to keep a lead's context for inbound callback recognition.
# After TTL expires the row is deleted and the agent asks name from scratch.
LEAD_TTL_DAYS      = int(os.environ.get("LEAD_TTL_DAYS", "30"))

app = FastAPI(title="AI Telecaller Dispatch")


# ─── DB (two tables: tenants + known_leads) ────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    customer_name      TEXT PRIMARY KEY,    -- matches ALR's payload field
    dealership_name    TEXT NOT NULL,
    agent_persona      TEXT DEFAULT 'John',
    language           TEXT DEFAULT 'hi-IN',
    voice              TEXT DEFAULT 'rahul',
    transfer_to        TEXT,
    inbound_did        TEXT,                -- DID Vobiz routes inbound calls from
    extra_prompt       TEXT DEFAULT '',
    callback_url       TEXT NOT NULL,       -- where the AGENT posts results
    is_active          INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_tenants_did ON tenants(inbound_did);

-- Separate table so high-volume lead writes never slow down tenant lookups.
-- One row per (phone, dealership). Upserted on every /dispatch call.
-- Inbound agent hits GET /lead/by-phone before greeting to load context.
CREATE TABLE IF NOT EXISTS known_leads (
    phone              TEXT NOT NULL,       -- E.164, e.g. +919876543210
    customer_name      TEXT NOT NULL,       -- dealership key (FK to tenants)
    lead_json          TEXT NOT NULL,       -- full ALR lead payload as JSON
    updated_at         INTEGER DEFAULT (strftime('%s','now')),
    expires_at         INTEGER NOT NULL,    -- epoch seconds; cleaned up by /healthz
    PRIMARY KEY (phone, customer_name)
);
-- Fast lookup by phone+dealership (hot path: inbound agent at call start)
CREATE INDEX IF NOT EXISTS idx_leads_phone ON known_leads(phone, customer_name);
-- Fast TTL cleanup (runs every 5 min via /healthz + UptimeRobot)
CREATE INDEX IF NOT EXISTS idx_leads_expires ON known_leads(expires_at);
"""


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


init_db()


# ─── Mount the admin UI (HTML + JSON CRUD) ─────────────────────────────
from admin import router as admin_router   # noqa: E402  (after init_db)
app.include_router(admin_router)


# ─── Models ────────────────────────────────────────────────────────────
class DispatchResponse(BaseModel):
    status:  str = "dispatched"
    room:    str
    dispatch_id: str


# ─── Endpoint ──────────────────────────────────────────────────────────
@app.post("/dispatch", response_model=DispatchResponse, status_code=202)
async def dispatch(
    lead: dict[str, Any],
    x_api_key: str = Header(...),
):
    if x_api_key != SHARED_API_KEY:
        raise HTTPException(401, "bad api key")

    customer_name = lead.get("customer_name")
    phone         = lead.get("phone")
    lead_id       = lead.get("lead_id")
    if not (customer_name and phone and lead_id):
        raise HTTPException(400, "missing customer_name / phone / lead_id")

    # 1. Resolve tenant
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM tenants WHERE customer_name = ? AND is_active = 1",
            (customer_name,),
        ).fetchone()
    if not row:
        raise HTTPException(404, f"tenant '{customer_name}' not configured")

    tenant = dict(row)

    # 2. Normalize phone (very simple — assume India)
    phone = _normalize_phone(phone)

    # 3. Build the metadata blob the agent will read
    room_name = f"out-{lead_id}-{int(time.time())}"
    metadata = {
        "direction": "outbound",
        "tenant": {
            "customer_name":   tenant["customer_name"],
            "dealership_name": tenant["dealership_name"],
            "agent_persona":   tenant["agent_persona"],
            "language":        tenant["language"],
            "voice":           tenant["voice"],
            "transfer_to":     tenant["transfer_to"],
            "extra_prompt":    tenant["extra_prompt"],
            "callback_url":    tenant["callback_url"],
            "callback_key":    AGENT_API_KEY,
        },
        "lead":         {**lead, "phone": phone},
        "phone_number": phone,
    }

    # 4. Dispatch via LiveKit (it queues, retries, and scales for us)
    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    try:
        result = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=OUTBOUND_AGENT,
                room=room_name,
                metadata=json.dumps(metadata),
            )
        )
    finally:
        await lkapi.aclose()

    # 5. Store lead for inbound callback recognition.
    #    INSERT OR REPLACE keeps only the freshest data per (phone, dealership).
    #    expires_at is calculated in Python so it uses LEAD_TTL_DAYS at runtime.
    expires_at = int(time.time()) + LEAD_TTL_DAYS * 86400
    with db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO known_leads (phone, customer_name, lead_json, updated_at, expires_at)
            VALUES (?, ?, ?, strftime('%s','now'), ?)
            """,
            (phone, customer_name, json.dumps(lead), expires_at),
        )
        conn.commit()

    return DispatchResponse(room=room_name, dispatch_id=result.id)


# ─── Lead context lookup (called by inbound agent at call start) ────────
@app.get("/lead/by-phone")
def lead_by_phone(
    phone: str,
    customer_name: str,
    x_api_key: str = Header(...),
):
    """Return stored lead JSON for a given phone + dealership.

    Auth: same AGENT_API_KEY the agent uses for ALR callbacks.
    Returns {} if not found or expired (agent gracefully starts fresh).
    Called once per inbound call, before the greeting — not during conversation.
    """
    if x_api_key != AGENT_API_KEY:
        raise HTTPException(401, "bad api key")
    phone = _normalize_phone(phone)
    with db() as conn:
        row = conn.execute(
            "SELECT lead_json FROM known_leads "
            "WHERE phone = ? AND customer_name = ? AND expires_at > strftime('%s','now')",
            (phone, customer_name),
        ).fetchone()
    if row:
        return json.loads(row["lead_json"])
    return {}


@app.delete("/lead/by-phone")
def delete_lead(
    phone: str,
    customer_name: str,
    x_api_key: str = Header(...),
):
    """Delete a single lead from the known_leads store.

    Use for DPDP compliance (right-to-erasure) or manual ops.
    Auth: AGENT_API_KEY.
    """
    if x_api_key != AGENT_API_KEY:
        raise HTTPException(401, "bad api key")
    phone = _normalize_phone(phone)
    with db() as conn:
        conn.execute(
            "DELETE FROM known_leads WHERE phone = ? AND customer_name = ?",
            (phone, customer_name),
        )
        conn.commit()
    return {"ok": True}


@app.get("/healthz")
async def healthz():
    # TTL cleanup: delete expired leads. Runs every 5 min via UptimeRobot ping.
    # Single indexed DELETE — takes <1ms on SQLite, no new infrastructure needed.
    with db() as conn:
        deleted = conn.execute(
            "DELETE FROM known_leads WHERE expires_at < strftime('%s','now')"
        ).rowcount
        conn.commit()
    return {"ok": True, "expired_leads_purged": deleted}


# ─── Tiny helpers ──────────────────────────────────────────────────────
def _normalize_phone(raw: str) -> str:
    s = "".join(c for c in raw if c.isdigit() or c == "+")
    if s.startswith("+"):
        return s
    if len(s) == 10:
        return "+91" + s
    return "+" + s
