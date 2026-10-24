#!/usr/bin/env bash
# Upload synthetic docs for APP-1001 after `docker compose up -d` and `python -m services.dashboard.seed`
curl -s -F application_id=APP-1001 -F files=@samples/fire_noc.pdf -F files=@samples/state_noc.pdf http://localhost:8001/api/v1/documents/upload
