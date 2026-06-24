# Inbound calls — complete setup

## How it works (no webhook, no relay)

```
Lead phone ──► Vobiz DID ──► LiveKit inbound SIP trunk
                                       │
                                       ▼
                       LiveKit matches the DID against
                       a SIP Dispatch Rule (one per tenant)
                                       │
                                       ▼
                       Rule says: "create a room 'in-<slug>-...'
                                   dispatch 'inbound-caller' agent
                                   with metadata={'customer_name':'Lakshmi TATA'}"
                                       │
                                       ▼
                       agent.py entrypoint() sees direction='inbound',
                       looks up tenant in /app/tenants.db, greets, talks,
                       POSTs result to tenant.callback_url
```

**No webhook from LiveKit to your server. No relay through the API.**
LiveKit's SIP dispatch rule carries the tenant slug as metadata directly.

## One-time setup for inbound

### Step 1 — Provision the LiveKit inbound SIP trunk

Once for the whole project. Add **all 300 DIDs** here:

```bash
lk sip inbound-trunk create \
  --name vobiz-inbound \
  --numbers "+911140000000,+911140000001,+911140000002,..."
# → copy the returned ST_inbound_xxx ID
```

(Configure Vobiz's side to route incoming traffic for these DIDs to
LiveKit's SIP endpoint — Vobiz support can do this in 10 minutes.)

### Step 2 — Bake `tenants.db` into the inbound agent image

The inbound agent needs to read tenant config (voice, language, persona,
callback URL) from a SQLite file inside the container. Pull a fresh copy
from your VPS each time you onboard new dealerships:

```bash
# From your laptop in the agent/ directory
scp user@your-vps:/data/tenants.db ./tenants.db

# Now the Dockerfile.inbound's `COPY tenants.db /app/tenants.db` will work
```

### Step 3 — Deploy the inbound agent

```bash
cd agent/

# Push secrets specific to inbound (same as outbound + AGENT_NAME override)
lk agent secrets set \
  AGENT_NAME=inbound-caller \
  SIP_OUTBOUND_TRUNK_ID=ST_xxx \
  VOBIZ_CALLER_ID=+919999999999 \
  OPENAI_API_KEY=sk-... \
  SARVAM_API_KEY=sk-sarvam-... \
  SARVAM_STT_MODEL=saaras:v3 \
  SARVAM_TTS_MODEL=bulbul:v3 \
  TENANT_DB_PATH=/app/tenants.db \
  USD_INR=83

# Create + deploy the inbound agent
lk agent create --config livekit.inbound.toml --region ap-south-1
lk agent deploy --config livekit.inbound.toml
```

> ⚠️ If you already deployed the **outbound** agent in this LiveKit project,
> they coexist — they have different `agent_name` values and LiveKit routes
> dispatches by that name.

### Step 4 — Create one SIP dispatch rule per dealership

This script reads `tenants.db` and creates / refreshes one rule per DID
in a single command:

```bash
cd api/

export LIVEKIT_URL=wss://your-project.livekit.cloud
export LIVEKIT_API_KEY=APIxxx
export LIVEKIT_API_SECRET=secretxxx
export SIP_INBOUND_TRUNK_ID=ST_inbound_xxx   # from step 1

python sync_inbound_rules.py
```

Output:
```
  deleted old rule alr-inbound-lakshmi-tata
  deleted old rule alr-inbound-tristar-mg
  ✓ Lakshmi TATA              DID=+911140000000  → room prefix 'in-lakshmi-tata-'
  ✓ Tristar MG                DID=+911140000001  → room prefix 'in-tristar-mg-'

Created 2 inbound dispatch rules.
```

Run this script **every time you onboard or remove a dealership**. It's idempotent
— it deletes its old `alr-inbound-*` rules and recreates them from the current DB.

## Workflow for onboarding a new dealership

```bash
# 1. Edit tenants.example.json (or use your admin UI) — add the new row
#    with the customer_name, inbound_did, callback_url, etc.

# 2. On the VPS, re-seed:
python seed_tenants.py tenants.example.json

# 3. On your laptop, refresh the agent's tenant DB + dispatch rules:
scp user@your-vps:/data/tenants.db agent/tenants.db
lk agent deploy --config agent/livekit.inbound.toml   # rebuilds with new DB
python api/sync_inbound_rules.py                       # adds the new dispatch rule
```

Two `scp` + two `lk` calls + one Python script. ~3 minutes per dealership.

## Caller identification (optional)

By default the inbound agent greets generically with the dealership name and
asks "How can I help?". The caller's phone number is available as
`participant.attributes["sip.phoneNumber"]` if you want to look up the lead
by phone.

To add caller-by-phone lookup, expose `GET /lead-by-phone?phone=+91...` on
ALR (see `docs/alr_changes.md` §4) and patch `agent.py` `entrypoint()`:

```python
if direction == "inbound" and agent.participant:
    caller = agent.participant.attributes.get("sip.phoneNumber")
    if caller and tenant.get("callback_url"):
        # ALR exposes the same base URL with /lead-by-phone
        lookup_url = tenant["callback_url"].rsplit("/", 1)[0] + "/lead-by-phone"
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(lookup_url, params={"phone": caller},
                                headers={"X-API-Key": os.environ["AGENT_API_KEY"]})
                if r.status_code == 200:
                    lead = r.json().get("lead") or {}
                    agent.lead = lead
                    agent.name = lead.get("name") or ""
        except Exception:
            pass  # fall back to generic greeting
```

Add this in v1.1 once you've validated the basic inbound flow works.

## Testing inbound

```bash
# 1. Call the DID from your own mobile
# 2. Watch logs
lk agent logs -f --agent-name inbound-caller

# 3. You should see:
#    "connecting to room in-lakshmi-tata-..."
#    "Hello, thanks for calling Lakshmi TATA Motors. This is John..."
#    "posting result to https://crm.lakshmitata.com/..."
```

## Common gotchas

| Problem | Cause / Fix |
|---|---|
| "No SIP trunk matched" in LiveKit logs | DID not listed in inbound trunk `numbers`, OR caller IP not in Vobiz's allowed list |
| Agent greets generically even though tenant exists | `tenants.db` inside the agent image is stale — rebuild + redeploy |
| `customer_name` mismatch | The string in `tenants.db` MUST match the metadata in the dispatch rule exactly — `sync_inbound_rules.py` guarantees this |
| Inbound rings forever, never picks up | Inbound agent has 0 replicas / hit max_replicas — check `lk agent status` |
| Two rules for the same DID | Old manual rules from testing — run `sync_inbound_rules.py` to clean up (it deletes all `alr-inbound-*` first) |
