#!/bin/bash
# ponytail: Using Docker for FreeSWITCH avoids 30 minutes of compilation and dependency hell.

set -e

echo "Building FreeSWITCH Docker image..."
docker build -t freeswitch-mod-audio-stream -f Dockerfile.freeswitch .

echo "Running FreeSWITCH container..."
# Stop existing if any
docker stop freeswitch-agent || true
docker rm freeswitch-agent || true

docker run -d \
  --name freeswitch-agent \
  --network host \
  freeswitch-mod-audio-stream

echo "Done! FreeSWITCH is running in Docker. Check with 'docker logs -f freeswitch-agent'"
