# Implementation Plan for AI Voice Agent V1 (FreeSWITCH + Deterministic Hybrid)

This plan details the end-to-end implementation of the AI Voice Agent for Automotive Lead Qualification. It is designed to comfortably handle **5,000 calls/day across 300 agencies** using a robust Dockerized architecture with 5 critical production reinforcements.

We are using a single-service Python `api/main.py` backend to handle both CRM webhooks AND the real-time FreeSWITCH WebSocket, completely eliminating the need for Node.js.

## Architecture Highlights
- **FreeSWITCH (Dockerized)**: Custom compiled image with `mod_audio_stream`. Handles all SIP, RTP, and audio stream routing. Extremely lightweight and fast.
- **FastAPI (Python Docker Container)**: Handles `POST /dispatch` from ALR, manages the SQLite tenant DB, and exposes a `ws://` endpoint to receive the raw audio from FreeSWITCH.
- **FreeSWITCH Dialplan**: XML routing rules that instruct FreeSWITCH to answer calls and pipe audio out to the Python WebSocket.
- **Async ESL (Greenswitch)**: Persistent TCP connection to FreeSWITCH (port 8021) for outbound calls and channel variables.
- **Audio Buffering & Caching**: 1-2 second chunk buffering for Sarvam STT stability, and `lru_cache`/`diskcache` for Sarvam TTS speed.

## Proposed Changes

### Core Infrastructure (Docker & Telephony)

#### [MODIFY] [docker-compose.yml](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/docker-compose.yml)
Update the existing compose file to include the Python API container, ensuring it shares a network with FreeSWITCH so Greenswitch and WebSockets can communicate via internal DNS (e.g., `ws://api:8000/ws`).

#### [NEW] [conf/dialplan/default.xml](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/conf/dialplan/default.xml)
Custom FreeSWITCH dialplan. When a call is connected, it executes the `audio_stream` application pointing to the FastAPI WebSocket endpoint.

#### [NEW] [conf/autoload_configs/event_socket.conf.xml](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/conf/autoload_configs/event_socket.conf.xml)
Update the ESL configuration to bind to `0.0.0.0` and set a secure password so the Python container can execute originate commands.

---

### API & Core Engine (Python only)

#### [MODIFY] [api/requirements.txt](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/requirements.txt)
Add `fastapi`, `uvicorn`, `pydantic`, `websockets`, `greenswitch`, `diskcache`.

#### [MODIFY] [api/main.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/main.py)
1. **ESL Connection Management**: Initialize `greenswitch.InboundESL` on startup with persistent connection and graceful shutdown.
2. **`/dispatch` Endpoint**: Executes the FreeSWITCH `originate` command non-blockingly via Greenswitch, passing the lead metadata.
3. **`/ws/{call_id}` Endpoint**: A FastAPI WebSocket route with 5s ping/pong heartbeat and reconnect logic to handle `mod_audio_stream` disconnects gracefully.

#### [NEW] [api/tenant_manager.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/tenant_manager.py)
Multi-tenancy config loader. Separated from `main.py` to efficiently cache and load the specific dealership config/prompts during 50+ concurrent calls.

#### [NEW] [api/esl_client.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/esl_client.py)
Dedicated Greenswitch wrapper for outbound origination and playing audio files directly on FreeSWITCH channels asynchronously.

#### [NEW] [api/logger.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/logger.py)
Posts final call results back to the tenant's `callback_url`. Maps outcomes to `status.py` integers:
- HOT / POSITIVE -> `2` or `3`
- BUSY -> `17`
- LATER -> `15`
- ALREADY PURCHASED -> `16`
- NOT INTERESTED -> `8`
- NO ANSWER / DROPPED -> `7`
- TRANSFER -> `17` (with transfer remark)

---

### Conversation & Fault Tolerance

#### [NEW] [api/state_machine.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/state_machine.py)
A lightweight state machine running inside the Python WebSocket loop. Dictates audio playback based on the detected voice intent from `flow.txt`.

#### [NEW] [api/intent_router.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/intent_router.py)
4-layer intent classification system (Regex, Keyword matching, Fuzzy matching, LLM fallback using `groq`).

#### [NEW] [api/circuit_breaker.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/circuit_breaker.py)
API fault tolerance to handle rate-limiting from Sarvam/Groq gracefully under load.

---

### Telephony, Buffering, & Audio

#### [NEW] [api/audio_buffer.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/audio_buffer.py)
Accumulates 20ms PCM chunks from FreeSWITCH into 1-2 second buffers before pushing to Sarvam STT to prevent hallucination and streaming errors.

#### [NEW] [api/audio_engine.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/audio_engine.py)
Handles dynamic TTS and pre-recorded files. Includes `functools.lru_cache` and `diskcache` implementations to meet the 15% cache hit target and avoid slamming Sarvam TTS APIs. Includes WebSocket heartbeats.

#### [NEW] [api/sarvam_stt.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/sarvam_stt.py)
Connects to Sarvam's WebSocket to feed buffered audio chunks from the FreeSWITCH stream.

#### [NEW] [api/recording.py](file:///c:/Users/HP/Documents/voice-agent/AI-telecaller-v1-deterministic-hybrid/api/recording.py)
Triggers `record_session` in FreeSWITCH and manages the lifecycle of the resulting `.wav` files (e.g. S3/MinIO upload + 30 day TTL).
