# V1 Setup — start to first call in ~30 minutes

## Prerequisites (the actual minimum)

| | What | Cost |
|---|---|---|
| 1 | **LiveKit Cloud** account (Build tier free; Scale $500/mo when you cross ~5k min/mo) | $0 to start |
| 2 | **Vobiz SIP trunk** + at least one outbound caller ID | ₹0 setup, ~₹0.45/min |
| 3 | **STT/TTS API keys** (Sarvam, Deepgram, or Cartesia) | varies depending on provider |
| 4 | **LLM API keys** (OpenAI, Groq, or Anthropic) | varies depending on provider |
| 5 | **One VPS** (Hetzner CX22 in Falkenstein or Contabo in Singapore) | ₹500/mo |
| 6 | **One domain** (e.g. `voice.yourdomain.com`) with TLS via Caddy | ₹800/yr |
| 7 | **LiveKit CLI** (`brew install livekit-cli`) | free |

That's it. No Postgres, no Redis, no AWS.

## Step 1 — LiveKit Cloud + Vobiz trunk (5 min)

```bash
# Login
lk cloud auth

# Outbound trunk (LiveKit → Vobiz)
lk sip outbound-trunk create \
  --name vobiz-outbound \
  --address sip.vobiz.com:5060 \
  --numbers "+91YOUR_CALLER_ID" \
  --auth-username "YOUR_VOBIZ_USER" \
  --auth-password "YOUR_VOBIZ_PASS"
# → copy the ST_xxxxxxxx ID

# Inbound trunk (Vobiz → LiveKit). Add all 300 DIDs here.
lk sip inbound-trunk create \
  --name vobiz-inbound \
  --numbers "+911140000000,+911140000001,..."
```

## Step 2 — Deploy the outbound agent to LiveKit Cloud (10 min)

```bash
cd agent
cp .env.example .env   # fill in Sarvam, OpenAI, Vobiz keys

# Push secrets to LiveKit Cloud (these become env vars in the worker container)
lk agent secrets set \
  SIP_OUTBOUND_TRUNK_ID=ST_xxx \
  VOBIZ_CALLER_ID=+919999999999 \
  LLM_PROVIDER=openai \
  OPENAI_API_KEY=sk-... \
  OPENAI_MODEL=gpt-4o-mini \
  STT_PROVIDER=sarvam \
  TTS_PROVIDER=sarvam \
  SARVAM_API_KEY=sk-sarvam-... \
  SARVAM_STT_MODEL=saaras:v3 \
  SARVAM_TTS_MODEL=bulbul:v3 \
  AGENT_NAME=outbound-caller \
  USD_INR=83

# Build + deploy (LiveKit Cloud builds Dockerfile.outbound remotely)
lk agent create --config livekit.outbound.toml --region ap-south-1
lk agent deploy --config livekit.outbound.toml

# Watch
lk agent logs -f --agent-name outbound-caller
```

For inbound (DIDs, dispatch rules, separate agent), see **`docs/inbound.md`**.

## Step 3 — Inbound (see `docs/inbound.md` for full detail)

Inbound is its own setup — separate agent deployment + one SIP dispatch rule
per DID. **Skip this for v1 launch if you only need outbound**; come back when
dealerships start asking "what happens when leads call us back?"

Quick summary:
1. Add the DID to `tenants.example.json` and re-seed.
2. Deploy the **inbound** agent: `lk agent deploy --config agent/livekit.inbound.toml`
   (uses `Dockerfile.inbound` which bakes `tenants.db`).
3. Run `python api/sync_inbound_rules.py` to create LiveKit SIP dispatch rules
   for every DID in one shot.

Full instructions: **`docs/inbound.md`**.

## Step 4 — Deploy the API on a VPS (10 min)

```bash
# On your VPS
ssh user@your-vps
git clone <your-repo>
cd alr-voice-agent-v1/api

cp .env.example .env  # fill in
openssl rand -hex 32  # → put in SHARED_API_KEY
openssl rand -hex 32  # → put in AGENT_API_KEY (also set on agent secrets!)

# Seed tenants
python seed_tenants.py tenants.example.json

# Build + run
docker build -t alr-api .
docker run -d --restart=always --name alr-api \
  -p 8080:8080 \
  --env-file .env \
  -v $PWD/data:/data \
  alr-api

# Caddy in front (auto-TLS)
cat > /etc/caddy/Caddyfile <<EOF
voice.yourdomain.com {
  reverse_proxy localhost:8080
}
EOF
sudo systemctl reload caddy
```

## Step 5 — Wire up ALR (5 min)

In your PHP CRM's "lead created" hook:

```php
$ch = curl_init('https://voice.yourdomain.com/dispatch');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'X-API-Key: ' . env('VOICE_SHARED_API_KEY'),
    ],
    CURLOPT_POSTFIELDS => json_encode($leadPayload),  // exactly your existing payload
    CURLOPT_RETURNTRANSFER => true,
]);
$resp = json_decode(curl_exec($ch), true);
$lead->ai_room = $resp['room'];
$lead->save();
```

And expose **one** receiver endpoint for the agent's callback:

```php
// routes/api.php
Route::post('/lead/ai-call-result', function (Request $req) {
    if ($req->header('X-API-Key') !== env('VOICE_AGENT_API_KEY')) abort(401);
    $d = $req->all();
    Lead::where('id', $d['lead_id'])->update([
        'ai_status_id' => $d['status_id'],
        'ai_remarks'   => $d['remarks'],
        'ai_cost_inr'  => $d['cost'],
        'ai_called_at' => $d['ended_at'],
        'ai_transcript_json' => json_encode($d['conversation']),
    ]);
    return response()->json(['ok' => true]);
});
```

## Step 6 — Test it

```bash
# Fire a fake lead
curl -X POST https://voice.yourdomain.com/dispatch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SHARED_API_KEY" \
  -d '{
    "customer_name": "Lakshmi TATA",
    "lead_id": 999,
    "name": "Test User",
    "phone": "+91YOUR_OWN_MOBILE",
    "model": "Seltos",
    "location": "Chennai"
  }'

# Watch logs
lk agent logs -f
```

Your phone should ring within 3 seconds.

## Done. That's the whole v1.

Total moving parts you operate:
- **1 VPS** running 1 Docker container (the API)
- **1 LiveKit Cloud project** with 1–2 agent deployments (outbound + inbound)
- **1 SQLite file** (tenants.db)

Compare to the v0 plan which had 7 services. This does the same job for 300 dealerships at 5k calls/day.

## When to add complexity (NOT in v1)

| Symptom | When | What to add |
|---|---|---|
| API server overwhelmed at >100 RPS | Probably year 2 | Postgres + 2 replicas behind nginx |
| Dealerships need self-service config | When you have a sales team | Tiny admin UI on top of the same SQLite |
| Lost a few callbacks during ALR downtime | First time it bites | Add a `pending_callbacks` table on agent side |
| Need conversation analytics | When upselling premium tier | Pipe callbacks to BigQuery / Metabase |
| Cross-region traffic | If you expand beyond India | Multi-region LiveKit agent deployment |

Don't pre-build any of these. The current design lets you add each in a day when actually needed.
