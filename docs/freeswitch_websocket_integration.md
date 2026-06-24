# FreeSWITCH WebSocket Integration & Troubleshooting

This document explains Phase 1 of our AI Telecaller architecture: successfully streaming real-time audio from FreeSWITCH into our custom Python API via WebSockets using `mod_audio_stream`.

## 1. Architecture Overview

To process 5,000+ deterministic AI calls per day, we bypassed standard heavy wrappers and built a direct bridge:
1. **Telephony Engine:** FreeSWITCH (Dockerized) handles SIP, RTP, and NAT.
2. **Audio Streaming:** A custom-compiled `mod_audio_stream` C module inside FreeSWITCH forks the call's audio channel directly into a raw binary WebSocket stream.
3. **Brain/Logic:** A Python FastAPI backend running `uvicorn` receives the WebSocket stream and handles AI STT/TTS routing.

---

## 2. The Core Configuration

### The Dialplan (`conf/dialplan/default.xml`)
When a call arrives at extension `5555` (or `ai_agent`), FreeSWITCH executes the `uuid_audio_stream` application:

```xml
<extension name="ai_agent">
  <condition field="destination_number" expression="^5555$|^ai_agent$">
    <action application="set" data="api_on_answer=uuid_audio_stream ${uuid} start ws://host.docker.internal:8000/ws/${uuid} mono 8k"/>
    <action application="answer"/>
    <action application="park"/>
  </condition>
</extension>
```
*Note the URL: `ws://host.docker.internal:8000/ws/${uuid}`.* 
This bridges the isolated Docker network back to the host machine where our Python API sits during local development.

---

## 3. Major Hurdles Encountered & Solved

Getting the FreeSWITCH container to successfully establish a WebSocket connection to the host Python API involves several networking pitfalls. We encountered and solved three distinct hurdles:

### Hurdle 1: Uvicorn Binding to Localhost (`127.0.0.1`)
**The Problem:** 
By default, running `uvicorn main:app --port 8000` binds the Python server strictly to `127.0.0.1`. Docker containers operate in an entirely different subnet. When FreeSWITCH tried to hit `host.docker.internal:8000`, the host's OS blocked it because the Python process wasn't listening on the Docker network interface.

**The Fix:**
You **must** force Uvicorn to listen on all interfaces using the `--host 0.0.0.0` flag:
```bash
# WRONG (Blocks Docker):
uvicorn main:app --port 8000

# CORRECT (Allows Docker to connect):
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Hurdle 2: Docker Desktop's Broken DNS (`host.docker.internal`)
**The Problem:**
Even with Uvicorn listening on `0.0.0.0`, the FreeSWITCH logs (`docker logs freeswitch-ai-agent`) were spammed with `connection error` from `audio_streamer_glue.cpp:286`. 
Docker Desktop on Windows/Mac frequently fails to properly resolve `host.docker.internal` from inside containers.

**The Fix:**
We initially tested hardcoding the host's LAN IP (e.g., `192.168.31.164`) in the dialplan, which successfully bypassed DNS and proved the network was reachable. However, **hardcoding IPs breaks portability (especially on a VPS)**.

To fix this robustly and cleanly, we injected a Docker `extra_hosts` mapping natively into `docker-compose.yml`:
```yaml
services:
  freeswitch:
    image: freeswitch-mod-audio-stream:latest
    extra_hosts:
      - "host.docker.internal:host-gateway"
```
This forces Docker to explicitly map the `host.docker.internal` hostname directly to the host machine's gateway IP automatically, regardless of the environment.

### Hurdle 3: Volume Mounting Errors
**The Problem:**
We originally mapped the `./conf` directory to `/etc/freeswitch`, but the Debian image was compiled with FreeSWITCH residing at `/usr/local/freeswitch/etc/freeswitch`. The dialplan changes were being ignored.

**The Fix:**
Corrected the `docker-compose.yml` volumes to map exactly to the compile target:
```yaml
    volumes:
      - ./conf:/usr/local/freeswitch/etc/freeswitch
```

---

## 4. How to Test & Verify (For New Devs)

If you are a new developer spinning up the environment, follow these exact steps to verify the WebSocket bridge:

1. **Start the API:**
   Ensure you are in the `api/` directory and your virtual environment is active.
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Start FreeSWITCH:**
   ```bash
   docker-compose up -d
   ```

3. **Check FreeSWITCH Logs:**
   Ensure `mod_audio_stream` loaded successfully:
   ```bash
   docker logs freeswitch-ai-agent | grep "mod_audio_stream"
   ```

4. **Make the Test Call:**
   - Open a SIP Client (e.g., MicroSIP).
   - Dial: `5555`
   - **Expected Result in Python Terminal:**
     ```text
     INFO:     127.0.0.1:57970 - "WebSocket /ws/1dc8f484-cc6b-4ac2-908d-282f5db9a7b7" [accepted]
     [WebSocket] Call connected: 1dc8f484-cc6b-4ac2-908d-282f5db9a7b7
     INFO:     connection open
     [WebSocket] Received 50 audio frames...
     [WebSocket] Received 100 audio frames...
     ```

5. **Closing the Call:**
   When you hang up in MicroSIP, FreeSWITCH drops the TCP connection without a closing handshake. You will see a `Cannot call "receive" once a disconnect message has been received` error in Python. This is normal and is caught safely by standard `except WebSocketDisconnect:` logic.
