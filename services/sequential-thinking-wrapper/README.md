# Sequential Thinking Wrapper

This service exposes a Streamable-HTTP-style endpoint for DDG-Agent's Sequential Thinking integration.

## Local Run

```bash
cd services/sequential-thinking-wrapper
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Health check:

```bash
curl http://127.0.0.1:38001/health
```

Direct tool call:

```bash
curl -X POST http://127.0.0.1:38001/sequentialthinking \
  -H 'Content-Type: application/json' \
  -d '{"thought":"确认尽调主体和数据边界","thoughtNumber":1,"totalThoughts":3,"nextThoughtNeeded":true}'
```

MCP-style endpoint:

```bash
curl -X POST http://127.0.0.1:38001/mcp \
  -H 'Content-Type: application/json' \
  -d '{"thought":"拆分工商、财务、司法、行业证据需求","thoughtNumber":2,"totalThoughts":3,"nextThoughtNeeded":true}'
```

## Docker

```bash
cd services/sequential-thinking-wrapper
docker compose up -d --build
```

DDG-Agent backend config:

```text
ENABLE_SEQUENTIAL_THINKING=true
SEQUENTIAL_THINKING_TRANSPORT=streamable_http
SEQUENTIAL_THINKING_REMOTE_URL=http://127.0.0.1:38001/mcp
```
