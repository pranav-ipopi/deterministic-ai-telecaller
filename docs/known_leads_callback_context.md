# Inbound Callback Context (Known Leads)

This document explains how the "Known Leads" feature works. It allows the inbound AI agent to recognize callers who are calling back (e.g., after an RNR - Ring No Answer) and greet them personally by name and mention their car model of interest.

## Problem Statement

In the original V1 design, when an outbound call was dispatched, the agent received full context (lead name, car model, location) from the ALR CRM payload. However, if the lead didn't pick up and called back later on the dealership's DID, the inbound agent started completely blind. The inbound SIP dispatch rule only provided the `customer_name` (dealership slug), but no caller-specific information.

## Solution Architecture

To solve this, we introduced a lightweight `known_leads` table in the API's SQLite database, functioning as a 30-day contact book for the agent.

### 1. Storing Lead Context on Dispatch

When the ALR CRM triggers an outbound call via `POST /dispatch`, the API now intercepts the payload and upserts it into the `known_leads` table before dispatching to LiveKit.

- **Table**: `known_leads`
- **Primary Key**: `(phone, customer_name)` — One active lead context per phone number per dealership.
- **TTL**: Leads are stored with an `expires_at` timestamp (default: 30 days).

### 2. Inbound Agent Lookup

When a lead calls the dealership's DID:
1. The call hits LiveKit and triggers the inbound SIP dispatch rule.
2. The `inbound-caller` agent spins up.
3. Before saying "Hello", the agent extracts the caller's E.164 phone number from the SIP participant identity.
4. The agent fires a quick `GET /lead/by-phone?phone=...&customer_name=...` to the API.
5. If found, the agent loads the lead's name and car model into its context.

### 3. Personalized Greeting

Depending on the context found, the agent's greeting changes dynamically:
- **Found Name & Model**: *"Hi Rahul! This is John from Lakshmi TATA. Calling back about the Nexon?"*
- **Found Name Only**: *"Hi Rahul! This is John from Lakshmi TATA. How can I help you today?"*
- **Not Found (or Expired)**: *"Hello, thanks for calling Lakshmi TATA. This is John. How can I help?"*

## Data Lifecycle & Compliance (DPDP Act)

To prevent the database from growing unbounded and to comply with data privacy regulations:

1. **Automated TTL Cleanup**: We piggyback on the existing UptimeRobot pings. Every time `/healthz` is called (every 5 minutes), the API runs a fast indexed `DELETE` query to purge any rows where `expires_at < now()`. This requires zero extra infrastructure (no cron jobs).
2. **Admin UI Management**: The `/admin` UI includes a "Known Leads" status bar showing the total stored leads.
3. **Manual Purge**: The Admin UI provides buttons to "Purge expired" and "Purge all" leads on demand.

## Required Environment Variables

For the inbound agent to securely fetch the context from the API, it requires two environment variables (pushed as LiveKit secrets):
- `DISPATCH_API_URL`: The base URL of the API (e.g., `https://voice.yourdomain.com`).
- `AGENT_API_KEY`: The shared secret to authenticate the lookup.

## Fallback & Latency

- **Latency**: The API lookup happens asynchronously before the first `session.say()` call. Since the API and the LiveKit worker are in the same region, the overhead is ~50ms and happens before any audio is played to the caller.
- **Graceful Degradation**: If the API is unreachable, times out (3 seconds), or the lead doesn't exist, the agent silently swallows the error and falls back to the generic greeting. The call is never dropped.
