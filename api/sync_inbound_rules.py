"""Create / refresh LiveKit SIP Dispatch Rules from tenants.db.

For each tenant with an `inbound_did`, this creates one dispatch rule that:
  - Matches calls coming in on that DID
  - Creates a new room prefixed with the tenant slug
  - Dispatches `inbound-caller` agent with metadata={"direction":"inbound","customer_name":"..."}

Run this after seeding tenants and whenever you onboard a new dealership:
    python sync_inbound_rules.py

Idempotent: deletes existing rules tagged with `alr-inbound-` prefix and recreates them.
"""
import asyncio
import json
import os
import re
import sqlite3
import sys

from livekit import api

LIVEKIT_URL        = os.environ["LIVEKIT_URL"]
LIVEKIT_API_KEY    = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]
INBOUND_TRUNK_ID   = os.environ["SIP_INBOUND_TRUNK_ID"]    # set via env
DB_PATH            = os.environ.get("DB_PATH", "tenants.db")

RULE_PREFIX = "alr-inbound-"   # tag for rules we own; safe to delete + recreate


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40] or "tenant"


async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tenants = [dict(r) for r in conn.execute(
        "SELECT customer_name, inbound_did FROM tenants "
        "WHERE is_active = 1 AND inbound_did IS NOT NULL AND inbound_did != ''"
    ).fetchall()]
    conn.close()

    if not tenants:
        print("No tenants with inbound_did set. Nothing to do.")
        return

    lk = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    try:
        # 1. Delete existing alr-inbound-* rules so we get a clean refresh
        existing = await lk.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
        for r in existing.items:
            if (r.name or "").startswith(RULE_PREFIX):
                await lk.sip.delete_sip_dispatch_rule(
                    api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=r.sip_dispatch_rule_id)
                )
                print(f"  deleted old rule {r.name}")

        # 2. Create one rule per tenant DID
        created = 0
        for t in tenants:
            slug = _slug(t["customer_name"])
            rule_name = f"{RULE_PREFIX}{slug}"
            metadata = json.dumps({
                "direction":     "inbound",
                "customer_name": t["customer_name"],
            })

            rule = api.SIPDispatchRuleInfo(
                name=rule_name,
                trunk_ids=[INBOUND_TRUNK_ID],
                inbound_numbers=[t["inbound_did"]],
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix=f"in-{slug}-",
                    ),
                ),
                room_config=api.RoomConfiguration(
                    agents=[api.RoomAgentDispatch(
                        agent_name="inbound-caller",
                        metadata=metadata,
                    )],
                ),
            )
            await lk.sip.create_sip_dispatch_rule(
                api.CreateSIPDispatchRuleRequest(dispatch_rule=rule)
            )
            print(f"  ✓ {t['customer_name']:<30}  DID={t['inbound_did']}  → room prefix 'in-{slug}-'")
            created += 1

        print(f"\nCreated {created} inbound dispatch rules.")
    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(main())
