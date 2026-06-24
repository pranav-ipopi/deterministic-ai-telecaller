# V1 cost analysis

## Per 3-minute call (typical sales qualification)

| Component | Rate | Per call | Source |
|---|---|---|---|
| LiveKit Cloud — agent minute | $0.01/min | **₹2.49** | LiveKit pricing |
| LiveKit Cloud — SIP minute | $0.003/min | **₹0.75** | LiveKit pricing |
| Vobiz outbound | ₹0.45/min | **₹1.35** | your contract |
| Sarvam STT (saaras:v3) | ₹30/hr | **₹1.50** | Sarvam pricing |
| Sarvam TTS (bulbul:v3) | ₹30/10k chars | **~₹0.45** | Sarvam pricing |
| OpenAI gpt-4o-mini | $0.15/$0.60 per Mtok | **~₹0.11** | OpenAI pricing |
| **Total** | | **~₹6.65** | |

**Per minute: ~₹2.22**

> Note: in v1 we use LiveKit's built-in `session.usage` which reports the **actual**
> token / character / second counts for each provider — no estimates. The numbers
> above are typical; your real per-call numbers will be whatever those usage events
> report, multiplied by the rate constants in `agent.py`.

## At your scale

| Volume | Daily | Monthly |
|---|---|---|
| 3,000 calls/day (9,000 min) | **₹19,980** | **₹5.99 L** |
| 5,000 calls/day (15,000 min) | **₹33,300** | **₹9.99 L** |

## Fixed costs (v1)

| Item | Monthly |
|---|---|
| Hetzner CX22 VPS | ₹500 |
| Domain | ₹65 (~₹800/yr) |
| LiveKit Cloud Scale tier (once you cross ~5k min/mo) | ₹41,500 |
| **Total fixed** | **~₹42,000** |

**v1 total monthly for 5k calls/day: ~₹10.4 L variable + ₹42k fixed = ~₹10.8 L**

At **₹15/min** charged to dealerships → ₹22.5 L revenue → **~52% gross margin**.
At **₹20/min** → ₹30 L → **~64% gross margin**.

## What you skip vs v0 plan (savings)

| | v0 fixed cost | v1 |
|---|---|---|
| RDS Postgres | ₹2,500 | ₹0 (SQLite) |
| Elasticache Redis | ₹2,500 | ₹0 (not needed) |
| ECS Fargate / Cloud Run | ₹6,000 | ₹500 (VPS) |
| Cloudflare Pro | ₹1,600 | ₹0 (free tier fine) |
| Sentry/Grafana paid | ₹4,000 | ₹0 (use LiveKit dashboard + journalctl) |
| **Savings** | | **~₹16,000/mo** |
