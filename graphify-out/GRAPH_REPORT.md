# Graph Report - AI-telecaller-v1-deterministic-hybrid  (2026-06-24)

## Corpus Check
- 65 files · ~85,216 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 501 nodes · 547 edges · 51 communities (40 shown, 11 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ee20466`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]

## God Nodes (most connected - your core abstractions)
1. `ALR Voice Agent — V1 Setup From Scratch` - 18 edges
2. `db()` - 13 edges
3. `What You Must Do When Invoked` - 12 edges
4. `Install` - 12 edges
5. `/graphify` - 10 edges
6. `V1 Setup — start to first call in ~30 minutes` - 10 edges
7. `OutboundCaller` - 10 edges
8. `V1 Setup — start to first call in ~30 minutes` - 10 edges
9. `require_admin()` - 9 edges
10. `require_admin()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `list_tenants()` --calls--> `db()`  [INFERRED]
  api/admin.py → api/main.py
- `upsert_tenant()` --calls--> `db()`  [INFERRED]
  api/admin.py → api/main.py
- `delete_tenant()` --calls--> `db()`  [INFERRED]
  api/admin.py → api/main.py
- `leads_count()` --calls--> `db()`  [INFERRED]
  api/admin.py → api/main.py
- `purge_expired_leads()` --calls--> `db()`  [INFERRED]
  api/admin.py → api/main.py

## Import Cycles
- None detected.

## Communities (51 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (42): 2.1 Create a LiveKit project, 2.2 Authenticate the CLI against your project, 2.3 Create the Vobiz outbound SIP trunk, 2.4 Create the Vobiz inbound SIP trunk, 3.1 Spin up the VPS, 3.2 Point your domain at it, 3.3 Configure Caddy (auto-HTTPS), 4.1 Clone the repo on the VPS (+34 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (36): Agent, ALRAgent, _build_instructions(), _build_llm(), _compute_cost_inr(), entrypoint(), _extract_conversation(), _fetch_lead_context() (+28 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (21): admin_page(), delete_tenant(), leads_count(), list_tenants(), login_submit(), manual_sync(), purge_all_leads(), purge_expired_leads() (+13 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (31): admin_page(), delete_tenant(), leads_count(), list_tenants(), login_submit(), manual_sync(), purge_all_leads(), purge_expired_leads() (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (19): Antigravity CLI, Before / after, Claude Code, CodeWhale, Codex, Commands, Development, FAQ (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.30
Nodes (11): db(), delete_lead(), dispatch(), DispatchResponse, healthz(), init_db(), lead_by_phone(), _normalize_phone() (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (11): Caller identification (optional), Common gotchas, How it works (no webhook, no relay), Inbound calls — complete setup, One-time setup for inbound, Step 1 — Provision the LiveKit inbound SIP trunk, Step 2 — Bake `tenants.db` into the inbound agent image, Step 3 — Deploy the inbound agent (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (11): Caller identification (optional), Common gotchas, How it works (no webhook, no relay), Inbound calls — complete setup, One-time setup for inbound, Step 1 — Provision the LiveKit inbound SIP trunk, Step 2 — Bake `tenants.db` into the inbound agent image, Step 3 — Deploy the inbound agent (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.18
Nodes (10): Done. That's the whole v1., Prerequisites (the actual minimum), Step 1 — LiveKit Cloud + Vobiz trunk (5 min), Step 2 — Deploy the outbound agent to LiveKit Cloud (10 min), Step 3 — Inbound (see `docs/inbound.md` for full detail), Step 4 — Deploy the API on a VPS (10 min), Step 5 — Wire up ALR (5 min), Step 6 — Test it (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.18
Nodes (10): Columns, 🛠️ Common queries (paste-ready), 📊 Database: `tenants.db`, Example rows (what the data actually looks like), Indexes, 📦 Sizing (will SQLite hold up?), SQL definition (verbatim from `api/main.py`), Table: `tenants` (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.18
Nodes (10): Done. That's the whole v1., Prerequisites (the actual minimum), Step 1 — LiveKit Cloud + Vobiz trunk (5 min), Step 2 — Deploy the outbound agent to LiveKit Cloud (10 min), Step 3 — Inbound (see `docs/inbound.md` for full detail), Step 4 — Deploy the API on a VPS (10 min), Step 5 — Wire up ALR (5 min), Step 6 — Test it (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.20
Nodes (9): 1. Storing Lead Context on Dispatch, 2. Inbound Agent Lookup, 3. Personalized Greeting, Data Lifecycle & Compliance (DPDP Act), Fallback & Latency, Inbound Callback Context (Known Leads), Problem Statement, Required Environment Variables (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.20
Nodes (9): 1. Storing Lead Context on Dispatch, 2. Inbound Agent Lookup, 3. Personalized Greeting, Data Lifecycle & Compliance (DPDP Act), Fallback & Latency, Inbound Callback Context (Known Leads), Problem Statement, Required Environment Variables (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (8): Prerequisites, Step 1: Create a Client (Dealership), Step 2: Trigger the Outbound Call, Step 3: Answer the Call, Step 4: Verify the Results, Testing Outbound Calls (End-to-End Local Setup), Using Postman, Using PowerShell

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (22): API & Core Engine (Python only), Architecture Highlights, Conversation & Fault Tolerance, Core Infrastructure (Docker & Telephony), Implementation Plan for AI Voice Agent V1 (FreeSWITCH + Deterministic Hybrid), [MODIFY] [api/main.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/main.py), [MODIFY] [api/requirements.txt](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/requirements.txt), [MODIFY] [docker-compose.yml](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/docker-compose.yml) (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (8): Prerequisites, Step 1: Create a Client (Dealership), Step 2: Trigger the Outbound Call, Step 3: Answer the Call, Step 4: Verify the Results, Testing Outbound Calls (End-to-End Local Setup), Using Postman, Using PowerShell

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 18 - "Community 18"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (7): Admin UI — onboard dealerships in the browser, Features, Onboarding workflow (new shortest path), Security notes, Setup (3 env vars), What auto-sync does on each save, What's NOT in the UI (yet)

### Community 20 - "Community 20"
Cohesion: 0.25
Nodes (7): 1. DB migration, 2. Fire on lead creation, 3. Receive the result, 4. (Optional) Inbound — caller identification, 5. .env additions for ALR, ALR (PHP CRM) — changes needed, Compliance note (one line in your lead form)

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (7): 1. DB migration, 2. Fire on lead creation, 3. Receive the result, 4. (Optional) Inbound — caller identification, 5. .env additions for ALR, ALR (PHP CRM) — changes needed, Compliance note (one line in your lead form)

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (6): ALR AI Voice Agent — V1 (Simplified), Architecture (the v1), File tree, Stack at a glance, What lives where, What you actually need to provision (vs the old plan)

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (5): At your scale, Fixed costs (v1), Per 3-minute call (typical sales qualification), V1 cost analysis, What you skip vs v0 plan (savings)

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (7): Configure Default Mode, Deactivate, Levels, More, Ponytail Help, Skills, Update

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (3): main(), Create / refresh LiveKit SIP Dispatch Rules from tenants.db.  For each tenant wi, _slug()

### Community 27 - "Community 27"
Cohesion: 0.33
Nodes (5): At your scale, Fixed costs (v1), Per 3-minute call (typical sales qualification), V1 cost analysis, What you skip vs v0 plan (savings)

### Community 28 - "Community 28"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 30 - "Community 30"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 35 - "Community 35"
Cohesion: 0.12
Nodes (14): 1. Architecture Overview, 2. The Core Configuration, 3. Major Hurdles Encountered & Solved, 4. How to Test & Verify (For New Devs), FreeSWITCH WebSocket Integration & Troubleshooting, Hurdle 1: Uvicorn Binding to Localhost (`127.0.0.1`), Hurdle 2: Docker Desktop's Broken DNS (`host.docker.internal`), Hurdle 3: Volume Mounting Errors (+6 more)

### Community 41 - "Community 41"
Cohesion: 0.40
Nodes (4): Boundaries, Hunt, Output, Tags

### Community 42 - "Community 42"
Cohesion: 0.40
Nodes (4): Boundaries, Honesty boundary, Ponytail Gain, Scoreboard

### Community 43 - "Community 43"
Cohesion: 0.40
Nodes (4): Boundaries, Examples, Format, Scoring

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (3): main(), Create / refresh LiveKit SIP Dispatch Rules from tenants.db.  For each tenant wi, _slug()

### Community 45 - "Community 45"
Cohesion: 0.50
Nodes (3): Boundaries, Output, Scan

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (3): ESLClient, Establish a pure asyncio raw socket connection to FreeSWITCH ESL., Originates an outbound call via a SIP gateway.         When answered, the call i

## Knowledge Gaps
- **254 isolated node(s):** `Why Compile from Source?`, `The Dependency Minefield (What we fixed)`, `Multi-Stage Docker Build`, `VPS Deployment (Docker Compose)`, `Architecture Highlights` (+249 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `dispatch()` connect `Community 4` to `Community 1`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `db()` (e.g. with `delete_tenant()` and `leads_count()`) actually correct?**
  _`db()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Why Compile from Source?`, `The Dependency Minefield (What we fixed)`, `Multi-Stage Docker Build` to the rest of the system?**
  _286 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.046511627906976744 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05701754385964912 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.13768115942028986 - nodes in this community are weakly interconnected._