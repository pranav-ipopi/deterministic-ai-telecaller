"""
ALR Voice Agent — minimal multi-tenant dispatch API.

ONE endpoint: POST /dispatch
  - Auth: X-API-Key header (shared with ALR)
  - Body: the ALR lead JSON
  - Action: look up tenant by customer_name in tenants.db, then originate
    an outbound call via FreeSWITCH ESL.

WebSocket Endpoint: /ws/{call_id}
  - Accepts raw audio streams from FreeSWITCH mod_audio_stream.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import httpx

# ─── Config ────────────────────────────────────────────────────────────
SHARED_API_KEY     = os.environ.get("SHARED_API_KEY", "default-secret")
AGENT_API_KEY      = os.environ.get("AGENT_API_KEY", "default-agent-secret")
DB_PATH            = os.environ.get("DB_PATH", "tenants.db")
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

CREATE TABLE IF NOT EXISTS known_leads (
    phone              TEXT NOT NULL,       -- E.164, e.g. +919876543210
    customer_name      TEXT NOT NULL,       -- dealership key (FK to tenants)
    lead_json          TEXT NOT NULL,       -- full ALR lead payload as JSON
    updated_at         INTEGER DEFAULT (strftime('%s','now')),
    expires_at         INTEGER NOT NULL,    -- epoch seconds; cleaned up by /healthz
    PRIMARY KEY (phone, customer_name)
);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON known_leads(phone, customer_name);
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
from admin import router as admin_router   # noqa: E402
app.include_router(admin_router)

# ─── Events ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    pass

@app.on_event("shutdown")
async def shutdown_event():
    pass

# ─── Models ────────────────────────────────────────────────────────────
class DispatchResponse(BaseModel):
    status:  str = "dispatched"
    room:    str
    dispatch_id: str

# ─── Dispatch Endpoint ─────────────────────────────────────────────────
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

    # 2. Normalize phone
    phone = _normalize_phone(phone)

    # 3. Dispatch via FreeSWITCH ESL
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://127.0.0.1:8080/txtapi/originate",
                auth=("freeswitch", "works"),
                data=f"{{ignore_early_media=true,origination_caller_id_number={phone}}}sofia/gateway/default/{phone} &transfer(ai_agent XML default)"
            )
            if resp.status_code != 200 or "+OK" not in resp.text:
                print(f"FreeSWITCH Originate Failed: {resp.text}")
    except Exception as e:
        raise HTTPException(500, f"Failed to originate call: {str(e)}")

    # 4. Store lead context
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

    return DispatchResponse(room="freeswitch", dispatch_id=lead_id)

# ─── WebSocket Endpoint for mod_audio_stream ───────────────────────────
@app.websocket("/ws/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"[WebSocket] Call connected: {call_id}")
    
    frames_received = 0
    try:
        while True:
            # mod_audio_stream sends the stream data
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                frames_received += 1
                if frames_received % 50 == 0:  # Log every ~1 second of audio
                    print(f"[WebSocket] Received {frames_received} audio frames for {call_id}")
            elif "text" in data and data["text"]:
                print(f"[WebSocket] Metadata from {call_id}: {data['text']}")
                
    except WebSocketDisconnect:
        print(f"[WebSocket] Call disconnected: {call_id}")
    except Exception as e:
        print(f"[WebSocket] Error on {call_id}: {e}")

# ─── Lead context lookup ───────────────────────────────────────────────
@app.get("/lead/by-phone")
def lead_by_phone(
    phone: str,
    customer_name: str,
    x_api_key: str = Header(...),
):
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
