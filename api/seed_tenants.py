"""Seed/update tenants from a JSON file. Idempotent — re-run anytime.

Usage:
  python seed_tenants.py tenants.example.json
"""
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = "tenants.db"

if len(sys.argv) != 2:
    print("usage: python seed_tenants.py <tenants.json>")
    sys.exit(1)

data = json.loads(Path(sys.argv[1]).read_text())

conn = sqlite3.connect(DB_PATH)
conn.executescript("""
CREATE TABLE IF NOT EXISTS tenants (
    customer_name      TEXT PRIMARY KEY,
    dealership_name    TEXT NOT NULL,
    agent_persona      TEXT DEFAULT 'John',
    language           TEXT DEFAULT 'hi-IN',
    voice              TEXT DEFAULT 'rahul',
    transfer_to        TEXT,
    inbound_did        TEXT,
    extra_prompt       TEXT DEFAULT '',
    callback_url       TEXT NOT NULL,
    is_active          INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_tenants_did ON tenants(inbound_did);
""")

for t in data:
    conn.execute("""
        INSERT INTO tenants (customer_name, dealership_name, agent_persona, language,
                             voice, transfer_to, inbound_did, extra_prompt, callback_url, is_active)
        VALUES (:customer_name, :dealership_name, :agent_persona, :language,
                :voice, :transfer_to, :inbound_did, :extra_prompt, :callback_url, :is_active)
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
    """, {
        "customer_name":   t["customer_name"],
        "dealership_name": t["dealership_name"],
        "agent_persona":   t.get("agent_persona", "John"),
        "language":        t.get("language", "hi-IN"),
        "voice":           t.get("voice", "rahul"),
        "transfer_to":     t.get("transfer_to"),
        "inbound_did":     t.get("inbound_did"),
        "extra_prompt":    t.get("extra_prompt", ""),
        "callback_url":    t["callback_url"],
        "is_active":       int(t.get("is_active", True)),
    })

conn.commit()
print(f"Seeded {len(data)} tenants into {DB_PATH}")
