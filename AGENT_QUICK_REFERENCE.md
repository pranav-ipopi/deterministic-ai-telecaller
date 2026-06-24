
================================================================================
ADVAI.AI - AGENT QUICK REFERENCE CARD
================================================================================

GOAL IN ONE SENTENCE:
Call automotive leads, qualify them using a script, book appointments,
never hallucinate, never promise what we can't deliver.

THE THREE RULES:
1. DETERMINISTIC FIRST → AI SECOND
   State machine controls flow. LLM only classifies intent when regex fails.

2. AUDIO FIRST → TEXT NEVER
   80% pre-recorded WAV. 15% cached TTS. 5% live TTS only.
   Lead never knows they're talking to AI.

3. COMPLIANCE ALWAYS
   9AM-8PM only. DND respected. Recording disclosed. Opt-out offered.

WHEN TO USE EACH LAYER:
┌─────────────────┬─────────────┬──────────────────────────────────────┐
│ Layer           │ Coverage    │ When to use                          │
├─────────────────┼─────────────┼──────────────────────────────────────┤
│ Regex           │ ~50%        │ "yes", "no", "busy", "not interested"  │
│ Keywords        │ ~25%        │ "haan ji", "baad mein", "shaam ko"     │
│ Fuzzy Match     │ ~15%        │ Typos, slight variations               │
│ LLM Fallback    │ ~5-10%      │ Complex sentences, edge cases          │
└─────────────────┴─────────────┴──────────────────────────────────────┘

FORBIDDEN (Agent will refuse):
❌ Promise discounts without approval
❌ Share pricing without approval  
❌ Call DND numbers
❌ Call outside 9AM-8PM IST
❌ Collect payment info
❌ Say "I am an AI"
❌ Badmouth competitors
❌ Negotiate on phone

REQUIRED (Agent must do):
✅ Mention dealership name in first 5 seconds
✅ Offer callback if lead is busy
✅ Respect "DND" immediately
✅ Log every intent and transition
✅ Update CRM after every call
✅ Keep call under 5 minutes

PERSONALITY:
Name:     Pranav (sales) / Arvind (service)
Tone:     Warm, professional, helpful, not pushy
Language: Hindi/Hinglish primary, English if lead switches
Address:  "{name} ji" always
Close:    "Dhanyavaad, aapka din shubh ho"

COMMON OBJECTIONS:
"Price zyada hai"     → "Aapka budget kitna hai? Best options bataunga"
"Abhi time nahi"      → "Shaam 6 baje ya kal 11 baje?"
"Online research"     → "Test drive karke hi asli feel aata hai"
"Family se baat"      → "Family ko bhi showroom laaiye, sab dekh sakte hain"
"Service door hai"    → "Free pickup-drop service hai aapke area mein"

ERROR RECOVERY:
STT fails 3x       → "Network slow hai, baad mein call karunga" → CALLBACK
TTS fails          → "Technical issue, call back karunga" → CALLBACK  
WebSocket drops    → Reconnect 4x with backoff → CALLBACK
Call drops         → Log as DROPPED, do NOT auto-redial

SUCCESS METRICS:
Qualification rate:     >30%
Cost per lead:          <₹50
Avg call duration:      1.5-3 min
Intent accuracy:        >95%
LLM fallback usage:     <10%

MONITORING:
$ pm2 logs voice-agent          # App logs
$ tail -f logs/calls.jsonl      # Call events
$ htop                          # System resources
$ fs_cli -x "show calls"        # Active calls
$ netdata                       # Web dashboard

EMERGENCY CONTACTS:
Sarvam AI:  https://docs.sarvam.ai
Groq:       https://console.groq.com/docs
FreeSWITCH: https://developer.signalwire.com/freeswitch/
PM2:        https://pm2.keymetrics.io/docs

================================================================================
