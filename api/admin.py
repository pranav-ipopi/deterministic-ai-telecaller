"""Tiny admin UI for tenant onboarding.

Mounted at /admin by main.py. One HTML page + JSON endpoints. Single password
login (ADMIN_PASSWORD env var) → signed cookie session.

On every successful create/update/delete we re-run the LiveKit SIP dispatch rule
sync in-process so inbound routing always matches what's in tenants.db.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import re
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Cookie, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from livekit import api
from pydantic import BaseModel

from main import db   # reuse the same SQLite helper

router = APIRouter()


# ─── Config ───────────────────────────────────────────────────────────
ADMIN_PASSWORD     = os.environ.get("ADMIN_PASSWORD", "")
COOKIE_SECRET      = os.environ.get("ADMIN_COOKIE_SECRET") or secrets.token_hex(32)
COOKIE_NAME        = "alr_admin"
COOKIE_MAX_AGE     = 60 * 60 * 8       # 8 hours

LIVEKIT_URL        = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY    = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
SIP_INBOUND_TRUNK_ID = os.environ.get("SIP_INBOUND_TRUNK_ID", "")
INBOUND_AGENT      = os.environ.get("INBOUND_AGENT", "inbound-caller")
RULE_PREFIX        = "alr-inbound-"

if not ADMIN_PASSWORD:
    # Warn but don't crash so dev can still hit /healthz etc.
    import logging
    logging.getLogger("uvicorn.error").warning(
        "ADMIN_PASSWORD not set — admin UI is DISABLED"
    )


# ─── Cookie helpers ───────────────────────────────────────────────────
def _sign(value: str) -> str:
    mac = hmac.new(COOKIE_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{mac}"


def _verify(signed: str) -> Optional[str]:
    if not signed or "." not in signed:
        return None
    value, mac = signed.rsplit(".", 1)
    expected = hmac.new(COOKIE_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return None
    # value = "<issued_ts>"
    try:
        ts = int(value)
    except ValueError:
        return None
    if time.time() - ts > COOKIE_MAX_AGE:
        return None
    return value


def require_admin(alr_admin: Optional[str] = Cookie(default=None)):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "admin UI disabled (set ADMIN_PASSWORD)")
    if not _verify(alr_admin or ""):
        raise HTTPException(401, "login required")


# ─── Slug ─────────────────────────────────────────────────────────────
def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:40] or "tenant"


# ─── Login / logout ───────────────────────────────────────────────────
@router.get("/admin/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    err_html = f'<div class="err">{error}</div>' if error else ""
    return HTMLResponse(LOGIN_HTML.replace("{{ERROR}}", err_html))


@router.post("/admin/login")
def login_submit(password: str = Form(...)):
    if not ADMIN_PASSWORD or not hmac.compare_digest(password, ADMIN_PASSWORD):
        return RedirectResponse("/admin/login?error=Wrong+password", status_code=303)
    resp = RedirectResponse("/admin/", status_code=303)
    cookie_val = _sign(str(int(time.time())))
    resp.set_cookie(
        COOKIE_NAME, cookie_val,
        max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax",
        secure=False,  # set True behind HTTPS in production (Caddy handles TLS)
    )
    return resp


@router.get("/admin/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ─── Page ─────────────────────────────────────────────────────────────
@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/", response_class=HTMLResponse)
def admin_page(alr_admin: Optional[str] = Cookie(default=None)):
    if not ADMIN_PASSWORD:
        return HTMLResponse(
            "<h1>Admin UI disabled</h1><p>Set ADMIN_PASSWORD env var.</p>",
            status_code=503,
        )
    if not _verify(alr_admin or ""):
        return RedirectResponse("/admin/login", status_code=303)
    return HTMLResponse(ADMIN_HTML)


# ─── JSON API ─────────────────────────────────────────────────────────
class TenantIn(BaseModel):
    customer_name: str
    dealership_name: str
    agent_persona: str = "John"
    language: str = "hi-IN"
    voice: str = "rahul"
    transfer_to: Optional[str] = None
    inbound_did: Optional[str] = None
    extra_prompt: str = ""
    callback_url: str
    is_active: bool = True


@router.get("/admin/api/tenants")
def list_tenants(alr_admin: Optional[str] = Cookie(default=None)):
    require_admin(alr_admin)
    with db() as conn:
        rows = conn.execute(
            "SELECT customer_name, dealership_name, agent_persona, language, voice, "
            "transfer_to, inbound_did, extra_prompt, callback_url, is_active "
            "FROM tenants ORDER BY customer_name"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/admin/api/tenants")
async def upsert_tenant(t: TenantIn, alr_admin: Optional[str] = Cookie(default=None)):
    require_admin(alr_admin)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO tenants (customer_name, dealership_name, agent_persona, language,
                                 voice, transfer_to, inbound_did, extra_prompt,
                                 callback_url, is_active)
            VALUES (:cn, :dn, :ap, :lang, :v, :tt, :did, :ep, :cb, :ia)
            ON CONFLICT(customer_name) DO UPDATE SET
                dealership_name=excluded.dealership_name,
                agent_persona=excluded.agent_persona,
                language=excluded.language,
                voice=excluded.voice,
                transfer_to=excluded.transfer_to,
                inbound_did=excluded.inbound_did,
                extra_prompt=excluded.extra_prompt,
                callback_url=excluded.callback_url,
                is_active=excluded.is_active;
            """,
            {
                "cn":  t.customer_name, "dn": t.dealership_name,
                "ap":  t.agent_persona, "lang": t.language, "v": t.voice,
                "tt":  t.transfer_to,   "did":  t.inbound_did,
                "ep":  t.extra_prompt,  "cb":   t.callback_url,
                "ia":  int(t.is_active),
            },
        )
        conn.commit()

    sync_result = await _sync_inbound_rules()
    return {"ok": True, "sync": sync_result}


@router.delete("/admin/api/tenants/{customer_name}")
async def delete_tenant(customer_name: str, alr_admin: Optional[str] = Cookie(default=None)):
    require_admin(alr_admin)
    with db() as conn:
        conn.execute("DELETE FROM tenants WHERE customer_name = ?", (customer_name,))
        conn.commit()
    sync_result = await _sync_inbound_rules()
    return {"ok": True, "sync": sync_result}


@router.post("/admin/api/sync-inbound")
async def manual_sync(alr_admin: Optional[str] = Cookie(default=None)):
    require_admin(alr_admin)
    return await _sync_inbound_rules()


# ─── Known Leads management ───────────────────────────────────────────────────
@router.get("/admin/api/leads/count")
def leads_count(alr_admin: Optional[str] = Cookie(default=None)):
    """Total leads stored + how many are currently expired (not yet purged)."""
    require_admin(alr_admin)
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM known_leads").fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM known_leads WHERE expires_at < strftime('%s','now')"
        ).fetchone()[0]
    return {"total": total, "expired": expired}


@router.post("/admin/api/leads/purge-expired")
def purge_expired_leads(alr_admin: Optional[str] = Cookie(default=None)):
    """Delete only rows whose TTL has passed. Safe to run anytime."""
    require_admin(alr_admin)
    with db() as conn:
        deleted = conn.execute(
            "DELETE FROM known_leads WHERE expires_at < strftime('%s','now')"
        ).rowcount
        conn.commit()
    return {"ok": True, "deleted": deleted}


@router.post("/admin/api/leads/purge-all")
def purge_all_leads(alr_admin: Optional[str] = Cookie(default=None)):
    """Delete ALL leads regardless of TTL. Use for compliance resets.
    Inbound agents will ask callers for their names until /dispatch repopulates.
    """
    require_admin(alr_admin)
    with db() as conn:
        deleted = conn.execute("DELETE FROM known_leads").rowcount
        conn.commit()
    return {"ok": True, "deleted": deleted}


# ─── LiveKit SIP rule sync (in-process) ───────────────────────────────
async def _sync_inbound_rules() -> dict:
    """Delete all `alr-inbound-*` rules and recreate from current tenants.db.
    Returns a small status dict the UI can show."""
    if not (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET):
        return {"ok": False, "skipped": "LIVEKIT_* env not set"}
    if not SIP_INBOUND_TRUNK_ID:
        return {"ok": False, "skipped": "SIP_INBOUND_TRUNK_ID not set"}

    with db() as conn:
        rows = conn.execute(
            "SELECT customer_name, inbound_did FROM tenants "
            "WHERE is_active = 1 AND inbound_did IS NOT NULL AND inbound_did != ''"
        ).fetchall()
    tenants = [dict(r) for r in rows]

    lk = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    deleted = created = 0
    errors: list[str] = []
    try:
        existing = await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
        for r in existing.items:
            if (r.name or "").startswith(RULE_PREFIX):
                try:
                    await lk.sip.delete_sip_dispatch_rule(
                        api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=r.sip_dispatch_rule_id)
                    )
                    deleted += 1
                except Exception as e:
                    errors.append(f"delete {r.name}: {e}")

        for t in tenants:
            slug = _slug(t["customer_name"])
            metadata = json.dumps({"direction": "inbound", "customer_name": t["customer_name"]})
            rule = api.SIPDispatchRuleInfo(
                name=f"{RULE_PREFIX}{slug}",
                trunk_ids=[SIP_INBOUND_TRUNK_ID],
                inbound_numbers=[t["inbound_did"]],
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix=f"in-{slug}-",
                    ),
                ),
                room_config=api.RoomConfiguration(
                    agents=[api.RoomAgentDispatch(agent_name=INBOUND_AGENT, metadata=metadata)],
                ),
            )
            try:
                await lk.sip.create_sip_dispatch_rule(
                    api.CreateSIPDispatchRuleRequest(dispatch_rule=rule)
                )
                created += 1
            except Exception as e:
                errors.append(f"create {t['customer_name']}: {e}")
    finally:
        await lk.aclose()

    return {"ok": not errors, "deleted": deleted, "created": created, "errors": errors}


# ─── Inline HTML (no separate template files) ─────────────────────────
LOGIN_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>ALR Admin — Login</title>
<style>
  body{font-family:system-ui,-apple-system,sans-serif;background:#f4f4f7;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;color:#222}
  .box{background:#fff;padding:32px;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,.08);width:340px}
  h1{margin:0 0 4px;font-size:20px}
  p{margin:0 0 20px;color:#666;font-size:14px}
  input{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #d8d8df;border-radius:6px;font-size:14px}
  button{margin-top:14px;width:100%;padding:10px;background:#3b5cff;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer}
  button:hover{background:#2945e3}
  .err{background:#ffe7e7;color:#a3121e;padding:8px 12px;border-radius:6px;font-size:13px;margin-bottom:12px}
</style></head><body>
  <form class="box" method="post" action="/admin/login">
    <h1>AI Telecaller Admin</h1>
    <p>Sign in to manage dealerships.</p>
    {{ERROR}}
    <input type="password" name="password" placeholder="Admin password" autofocus required>
    <button>Sign in</button>
  </form>
</body></html>"""


ADMIN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>AI Telecaller — Client Management</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#f4f4f7;color:#222}
  header{background:#1f2333;color:#fff;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
  header h1{margin:0;font-size:16px;font-weight:600}
  header a{color:#aab;text-decoration:none;font-size:13px}
  .wrap{max-width:1200px;margin:24px auto;padding:0 16px}
  .bar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
  button{background:#3b5cff;color:#fff;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:13px}
  button.ghost{background:#fff;color:#3b5cff;border:1px solid #3b5cff}
  button.danger{background:#d93b3b}
  button:hover{filter:brightness(.94)}
  table{width:100%;background:#fff;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05)}
  th,td{padding:10px 12px;text-align:left;font-size:13px;border-bottom:1px solid #eee;vertical-align:middle}
  th{background:#fafaff;font-weight:600;color:#555;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  tr:last-child td{border-bottom:none}
  .badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
  .on{background:#dff7e2;color:#1e7a37}
  .off{background:#f3d6d6;color:#8e1c1c}
  .actions button{padding:5px 10px;font-size:12px;margin-right:4px}
  .modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);align-items:center;justify-content:center;z-index:50}
  .modal.show{display:flex}
  .card{background:#fff;width:560px;max-width:95vw;border-radius:12px;padding:22px;max-height:90vh;overflow-y:auto}
  .card h2{margin:0 0 14px;font-size:16px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px}
  .grid label{font-size:12px;color:#666;display:block;margin-bottom:3px}
  .grid input, .grid textarea, .grid select{
    width:100%;padding:8px 10px;border:1px solid #d8d8df;border-radius:6px;font-size:13px;font-family:inherit
  }
  .grid .full{grid-column:1/-1}
  .grid textarea{min-height:60px;resize:vertical}
  .foot{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
  .toast{position:fixed;bottom:20px;right:20px;background:#1f2333;color:#fff;padding:12px 16px;border-radius:8px;
         font-size:13px;box-shadow:0 6px 24px rgba(0,0,0,.2);opacity:0;transform:translateY(20px);transition:.2s}
  .toast.show{opacity:1;transform:none}
  .toast.err{background:#a3121e}
  .empty{padding:48px;text-align:center;color:#888;background:#fff;border-radius:10px}
  .small{font-size:11px;color:#888}
  .leads-bar{display:flex;align-items:center;gap:10px;background:#fff;border-radius:10px;
             padding:10px 16px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.05);flex-wrap:wrap}
  .leads-label{font-size:13px;flex:1 1 auto}
  .leads-sub{font-size:12px;color:#e07700}
  button.sm{padding:5px 10px;font-size:12px}
</style></head>
<body>
<header>
  <h1>🚗 AI Telecaller — Client Management</h1>
  <div>
    <a href="/docs" target="_blank">API docs</a> &nbsp;·&nbsp;
    <a href="/admin/logout">Logout</a>
  </div>
</header>

<div class="wrap">
  <div class="bar">
    <button id="add-btn">+ Add dealership</button>
    <button class="ghost" id="sync-btn">⟳ Sync inbound rules</button>
    <span id="status" class="small" style="align-self:center;margin-left:8px"></span>
  </div>

  <div class="leads-bar" id="leads-bar">
    <span class="leads-label">📞 Known leads: <b id="leads-count">…</b> stored</span>
    <span class="leads-sub" id="leads-expired"></span>
    <button class="ghost sm" id="purge-expired-btn">Purge expired</button>
    <button class="danger sm" id="purge-all-btn">Purge all</button>
  </div>

  <div id="content"></div>
</div>

<!-- Modal -->
<div class="modal" id="modal">
  <div class="card">
    <h2 id="modal-title">Add dealership</h2>
    <form id="form">
      <div class="grid">
        <div>
          <label>Customer name <span style="color:red">*</span> <span class="small">(must match ALR payload)</span></label>
          <input name="customer_name" required>
        </div>
        <div>
          <label>Dealership name <span style="color:red">*</span></label>
          <input name="dealership_name" required>
        </div>
        <div>
          <label>Agent persona</label>
          <input name="agent_persona" value="John">
        </div>
        <div>
          <label>Language</label>
          <select name="language">
            <option value="hi-IN">Hindi (hi-IN)</option>
            <option value="en-IN">English India (en-IN)</option>
            <option value="ta-IN">Tamil (ta-IN)</option>
            <option value="te-IN">Telugu (te-IN)</option>
            <option value="kn-IN">Kannada (kn-IN)</option>
            <option value="mr-IN">Marathi (mr-IN)</option>
            <option value="bn-IN">Bengali (bn-IN)</option>
            <option value="gu-IN">Gujarati (gu-IN)</option>
            <option value="ml-IN">Malayalam (ml-IN)</option>
            <option value="pa-IN">Punjabi (pa-IN)</option>
            <option value="or-IN">Odia (or-IN)</option>
          </select>
        </div>
        <div>
          <label>Voice (Sarvam speaker)</label>
          <select name="voice">
            <option value="rahul">rahul (male)</option>
            <option value="meera">meera (female)</option>
            <option value="vidya">vidya (female)</option>
            <option value="arvind">arvind (male)</option>
            <option value="amol">amol (male)</option>
            <option value="amartya">amartya (male)</option>
            <option value="diya">diya (female)</option>
            <option value="neel">neel (male)</option>
          </select>
        </div>
        <div>
          <label>Transfer-to number <span class="small">(human escalation)</span></label>
          <input name="transfer_to" placeholder="+919876543210">
        </div>
        <div>
          <label>Inbound DID <span class="small">(Vobiz number)</span></label>
          <input name="inbound_did" placeholder="+911140000000">
        </div>
        <div>
          <label>Active</label>
          <select name="is_active"><option value="1">Yes</option><option value="0">No</option></select>
        </div>
        <div class="full">
          <label>Callback URL <span style="color:red">*</span></label>
          <input name="callback_url" required placeholder="https://crm.example.com/api/lead/ai-call-result">
        </div>
        <div class="full">
          <label>Extra prompt <span class="small">(special offers, instructions for the agent)</span></label>
          <textarea name="extra_prompt" placeholder="Mention our Diwali offer if asked about price."></textarea>
        </div>
      </div>
      <div class="foot">
        <button type="button" class="ghost" id="cancel-btn">Cancel</button>
        <button type="submit">Save &amp; sync</button>
      </div>
    </form>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const $ = (s) => document.querySelector(s);
const modal = $("#modal"), form = $("#form"), titleEl = $("#modal-title");
let editingName = null;

function toast(msg, isErr=false){
  const t = $("#toast"); t.textContent = msg;
  t.classList.toggle("err", isErr); t.classList.add("show");
  setTimeout(()=>t.classList.remove("show"), 3500);
}

async function load(){
  const r = await fetch("/admin/api/tenants");
  if(r.status === 401){ location.href = "/admin/login"; return; }
  const tenants = await r.json();
  const wrap = $("#content");
  if(!tenants.length){
    wrap.innerHTML = `<div class="empty">No dealerships yet. Click <b>+ Add dealership</b> to onboard your first one.</div>`;
    $("#status").textContent = "";
    return;
  }
  $("#status").textContent = `${tenants.length} dealership(s)`;
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>Customer name</th><th>Dealership</th><th>Voice</th><th>Lang</th>
      <th>Inbound DID</th><th>Transfer</th><th>Status</th><th>Actions</th>
    </tr></thead>
    <tbody>${tenants.map(t => `<tr>
      <td><b>${escape(t.customer_name)}</b></td>
      <td>${escape(t.dealership_name)}</td>
      <td>${escape(t.voice)}</td>
      <td>${escape(t.language)}</td>
      <td>${escape(t.inbound_did || "—")}</td>
      <td>${escape(t.transfer_to || "—")}</td>
      <td><span class="badge ${t.is_active?'on':'off'}">${t.is_active?'active':'inactive'}</span></td>
      <td class="actions">
        <button class="ghost" data-edit='${JSON.stringify(t).replaceAll("'","&apos;")}'>Edit</button>
        <button class="danger" data-del="${escape(t.customer_name)}">Delete</button>
      </td>
    </tr>`).join("")}</tbody></table>`;

  wrap.querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>openModal(JSON.parse(b.dataset.edit)));
  wrap.querySelectorAll("[data-del]").forEach(b=>b.onclick=()=>del(b.dataset.del));
}

function escape(s){ return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

function openModal(t){
  editingName = t ? t.customer_name : null;
  titleEl.textContent = t ? `Edit ${t.customer_name}` : "Add dealership";
  form.reset();
  if(t){
    for(const k of Object.keys(t)){
      const f = form.elements[k];
      if(!f) continue;
      f.value = (k === "is_active") ? String(t[k] ? 1 : 0) : (t[k] ?? "");
    }
    form.elements["customer_name"].readOnly = true;
  } else {
    form.elements["customer_name"].readOnly = false;
  }
  modal.classList.add("show");
}

$("#add-btn").onclick = ()=>openModal(null);
$("#cancel-btn").onclick = ()=>modal.classList.remove("show");

form.onsubmit = async (e)=>{
  e.preventDefault();
  const fd = new FormData(form);
  const data = Object.fromEntries(fd.entries());
  data.is_active = data.is_active === "1";
  const r = await fetch("/admin/api/tenants", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify(data),
  });
  if(!r.ok){ toast("Save failed: " + await r.text(), true); return; }
  const j = await r.json();
  modal.classList.remove("show");
  if(j.sync && j.sync.errors && j.sync.errors.length){
    toast(`Saved. Sync had ${j.sync.errors.length} error(s) — see console.`, true);
    console.warn("Sync errors:", j.sync.errors);
  } else if(j.sync && j.sync.skipped){
    toast(`Saved. Sync skipped: ${j.sync.skipped}`);
  } else {
    toast(`Saved. Synced ${j.sync.created} inbound rules.`);
  }
  load();
};

async function del(name){
  if(!confirm(`Delete dealership "${name}"? This will also remove its inbound dispatch rule.`)) return;
  const r = await fetch("/admin/api/tenants/" + encodeURIComponent(name), {method:"DELETE"});
  if(!r.ok){ toast("Delete failed", true); return; }
  toast("Deleted.");
  load();
}

// ── Known Leads bar ────────────────────────────────────────────────────
async function loadLeadStats(){
  try{
    const r = await fetch("/admin/api/leads/count");
    if(!r.ok) return;
    const j = await r.json();
    $("#leads-count").textContent = j.total;
    $("#leads-expired").textContent = j.expired > 0 ? `(${j.expired} expired, pending purge)` : "";
  } catch(e){ $("#leads-count").textContent = "?"; }
}

$("#purge-expired-btn").onclick = async ()=>{
  const r = await fetch("/admin/api/leads/purge-expired", {method:"POST"});
  const j = await r.json();
  toast(`Purged ${j.deleted} expired lead(s).`);
  loadLeadStats();
};

$("#purge-all-btn").onclick = async ()=>{
  if(!confirm("Delete ALL stored leads? Inbound agents will ask callers for their name again until new calls are dispatched.")) return;
  const r = await fetch("/admin/api/leads/purge-all", {method:"POST"});
  const j = await r.json();
  toast(`Purged all ${j.deleted} lead(s).`, j.deleted > 0);
  loadLeadStats();
};

$("#sync-btn").onclick = async ()=>{
  $("#sync-btn").disabled = true; $("#sync-btn").textContent = "Syncing…";
  try{
    const r = await fetch("/admin/api/sync-inbound", {method:"POST"});
    const j = await r.json();
    if(j.skipped) toast("Sync skipped: " + j.skipped, true);
    else if(j.errors && j.errors.length) toast(`Sync had ${j.errors.length} error(s).`, true);
    else toast(`Synced. Deleted ${j.deleted}, created ${j.created}.`);
  } catch(e){ toast("Sync failed: " + e, true); }
  $("#sync-btn").disabled = false; $("#sync-btn").textContent = "⟳ Sync inbound rules";
};

load();
loadLeadStats();
</script>
</body></html>"""
