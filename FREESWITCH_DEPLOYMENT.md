# FreeSWITCH AI Voice Agent - Deployment & Build Guide

This document explains the architecture, dependencies, and gotchas involved in building and deploying the custom FreeSWITCH Docker container for the AI Telecaller project.

## Why Compile from Source?
To stream raw audio from phone calls to an AI agent in real-time, this project relies on a custom, community-built FreeSWITCH module called `mod_audio_stream`.
Because this is not an official module, it does not exist in standard package managers (like `apt-get`). To use it, we must compile it from source. Compiling a FreeSWITCH module requires the FreeSWITCH core source code, which in turn forces us to compile FreeSWITCH from scratch.

## The Dependency Minefield (What we fixed)
Over the years, the creators of FreeSWITCH decoupled several core libraries into separate repositories. This Dockerfile successfully navigates the following historical dependency traps so you don't have to:

1. **`spandsp` API Changes:** The master branch of `spandsp` introduced breaking API changes (e.g., renaming `V18_MODE_5BIT_4545`). The Dockerfile explicitly checks out the stable commit `67d2455` to maintain compatibility with FreeSWITCH 1.10.x.
2. **Missing `sofia-sip`:** Removed from the main source tree in v1.10.4, this must be cloned and compiled manually before FreeSWITCH.
3. **The `libks` / SignalWire Trap:** By default, FreeSWITCH tries to compile `mod_verto` and `mod_signalwire`, which require a library called `libks`. We use `sed` to automatically disable these modules in `modules.conf` to avoid the error.
4. **`libevent` for WebSockets:** The `mod_audio_stream` module uses a submodule (`libwsc`) for WebSockets, which requires the C library `libevent-dev` to compile and run.
5. **Missing Default Configs:** `make install` does not install configuration files. We explicitly copy the `conf/vanilla` folder to ensure FreeSWITCH has the base configuration required to start.

## Multi-Stage Docker Build
The `Dockerfile.freeswitch` uses a two-stage build:
- **Stage 1 (Builder):** Installs compilers, downloads gigabytes of source code, and compiles everything.
- **Stage 2 (Production):** A pristine Ubuntu environment where we only copy the final compiled `.so` files and binaries. This keeps the final VPS deployment image small and secure.

## VPS Deployment (Docker Compose)
When deploying to a Linux VPS for production, simply uncomment `network_mode: "host"` in the `docker-compose.yml` file. 

**Why?**
FreeSWITCH uses a massive range of UDP ports (16384-32768) for RTP audio streams. Mapping 16,000 individual ports through Docker's standard bridge network (`-p 16384-32768:16384-32768/udp`) can consume gigabytes of RAM and instantly crash the Docker daemon. 

Host networking bypasses Docker's proxy entirely, allowing the FreeSWITCH container to bind directly to the server's network interfaces. This completely eliminates port-mapping memory overhead and avoids complex NAT audio routing issues. 

By running FreeSWITCH with host networking, a single modern VPS can easily and efficiently handle your production target of **5,000 calls a day** (100-150 concurrent calls) without Docker breaking a sweat.

See `docker-compose.yml` for the standard configuration.
