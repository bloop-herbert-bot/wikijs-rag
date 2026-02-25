# wikijs-search Plugin

OpenClaw plugin that provides semantic search across Wiki.js documentation using RAG (Retrieval-Augmented Generation).

## Features

- **`wikijs_search`** - Search Wiki.js docs with natural language
- **`wikijs_health`** (optional) - Check RAG API status

## Installation

1. **Install plugin:**
   ```bash
   mkdir -p ~/.openclaw/plugins/wikijs-search
   cp index.mjs package.json ~/.openclaw/plugins/wikijs-search/
   ```

2. **Enable in OpenClaw config:**
   ```json
   {
     "plugins": {
       "installed": ["wikijs-search"]
     }
   }
   ```

3. **Start RAG API:**
   ```bash
   cd ~/.openclaw/workspace-githerbert/wikijs-rag
   source venv/bin/activate
   uvicorn rag_api:app --host 0.0.0.0 --port 8765 &
   ```

## Usage

The `wikijs_search` tool is automatically available to all agents:

```
User: What is the IP address of ioBroker?

Agent: Let me search the Wiki.js documentation...
[calls wikijs_search with query="ioBroker IP address"]

According to Container/iobroker page, ioBroker runs on 192.168.0.110 (Container 100).
```

## Configuration

Set `RAG_API_URL` environment variable to override default:

```bash
export RAG_API_URL=http://localhost:8765
```

## Optional Tools

Enable health check tool in agent config:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["wikijs_health"]
        }
      }
    ]
  }
}
```

## Prerequisites

- RAG API running on port 8765
- ChromaDB indexed with Wiki.js content
- Ollama with `nomic-embed-text` model

## Troubleshooting

**Tool not available:**
- Check plugin is enabled in config
- Restart OpenClaw gateway: `openclaw gateway restart`

**Connection errors:**
- Verify RAG API is running: `curl http://localhost:8765/health`
- Check firewall/network settings

**No results:**
- Verify ChromaDB has data: `curl http://localhost:8765/stats`
- Reindex if needed: `python3 rag_indexer.py`

## Development

Test the tool directly:

```bash
# From OpenClaw agent:
wikijs_search({query: "Grafana IP", top_k: 3})

# CLI test:
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Grafana IP", "top_k": 3}'
```

## License

MIT
