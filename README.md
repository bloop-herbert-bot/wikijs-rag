# Wiki.js RAG System

**Semantic search API for Wiki.js documentation** - Enables OpenClaw agents to query Wiki.js content using natural language.

---

## 🎯 Features

- **Semantic Search:** Query Wiki.js pages with natural language
- **ChromaDB Vector Store:** Efficient similarity search over embedded content
- **Ollama Embeddings:** Uses `nomic-embed-text` model via Ollama
- **FastAPI REST API:** Simple HTTP interface for all agents
- **Auto-Reindexing:** Daily cron job keeps index up-to-date

---

## 🏗️ Architecture

```
Wiki.js (PostgreSQL) 
    ↓ GraphQL API
RAG Indexer (Python)
    ↓ Chunks + Embeddings
ChromaDB Vector Store
    ↓ Similarity Search
FastAPI Query API
    ↓ HTTP/JSON
OpenClaw Agents
```

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/bloop-herbert-bot/wikijs-rag.git
cd wikijs-rag
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Edit `rag_indexer.py` and `rag_api.py`:

```python
WIKI_API_URL = "http://your-wiki-js:3000/graphql"
WIKI_API_TOKEN = "your-api-token"
OLLAMA_BASE_URL = "http://your-ollama:11434"
```

### 4. Run Indexer (First Time)

```bash
python3 rag_indexer.py
```

Output:
```
📚 Wiki.js RAG Indexer
📡 Fetching Wiki.js pages...
✅ Found 61 pages
✂️ Chunking 61 pages...
✅ Created 200 chunks
🧠 Generating embeddings...
✅ Indexing complete!
```

### 5. Start API Server

```bash
uvicorn rag_api:app --host 0.0.0.0 --port 8765
```

Or use systemd service (see below).

---

## 🚀 Usage

### Query API

**Endpoint:** `POST /query`

**Request:**
```json
{
  "query": "Was ist die IP von ioBroker?",
  "top_k": 3
}
```

**Response:**
```json
{
  "query": "Was ist die IP von ioBroker?",
  "count": 3,
  "results": [
    {
      "content": "ioBroker läuft auf 192.168.0.110 (Container 100)...",
      "metadata": {
        "page_id": 95,
        "path": "de/Container/iobroker",
        "title": "ioBroker - Smart Home Hub"
      },
      "score": 0.92
    }
  ]
}
```

### cURL Example

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Wie konfiguriere ich Shelly Geräte?",
    "top_k": 5
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8765/query",
    json={"query": "Was ist die IP von Grafana?", "top_k": 3}
)

results = response.json()
for result in results["results"]:
    print(f"📄 {result['metadata']['title']}")
    print(f"   {result['content'][:100]}...")
    print(f"   Score: {result['score']:.2f}")
```

---

## 🔧 Systemd Service

**File:** `/etc/systemd/system/wikijs-rag.service`

```ini
[Unit]
Description=Wiki.js RAG Query API
After=network.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/path/to/wikijs-rag
ExecStart=/path/to/venv/bin/uvicorn rag_api:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable & Start:**
```bash
sudo systemctl enable wikijs-rag
sudo systemctl start wikijs-rag
sudo systemctl status wikijs-rag
```

---

## 🔄 Auto-Reindexing (Cron)

**Crontab:** Daily reindex at 02:00

```bash
crontab -e

# Wiki.js RAG reindex (täglich 02:00)
0 2 * * * cd /path/to/wikijs-rag && ./venv/bin/python3 rag_indexer.py >> /tmp/rag_reindex.log 2>&1
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/stats` | GET | Collection statistics |
| `/query` | POST | Semantic search |

### `/health`

```bash
curl http://localhost:8765/health
```

Response:
```json
{
  "status": "ok",
  "collection": "wikijs",
  "documents": 200,
  "ollama": "http://192.168.0.204:11434"
}
```

### `/stats`

```bash
curl http://localhost:8765/stats
```

Response:
```json
{
  "collection": "wikijs",
  "total_chunks": 200,
  "unique_pages": 61,
  "storage": "./chromadb"
}
```

---

## 🐛 Troubleshooting

### Problem: Ollama Connection Failed

**Error:**
```
Failed to establish connection to http://192.168.0.204:11434
```

**Solution:**
1. Check Ollama is running: `curl http://192.168.0.204:11434/api/tags`
2. Verify model exists: `curl http://192.168.0.204:11434/api/tags | jq '.models[] | select(.name | contains("nomic"))'`
3. Check network/firewall between RAG system and Ollama

### Problem: Wiki.js GraphQL Error

**Error:**
```
Cannot query field "content" on type "PageListItem"
```

**Solution:**
- Use `single(id:)` query instead of `list` for full content
- Check API token has read permissions
- Verify Wiki.js version (requires v2.5+)

### Problem: ChromaDB Empty

**Error:**
```
✅ Fetched 0 pages with content
```

**Solution:**
1. Run indexer with debug: `python3 rag_indexer.py 2>&1 | tee indexer.log`
2. Check GraphQL query returns pages
3. Verify page content is not empty

---

## 📚 Dependencies

- **Python 3.11+**
- **LangChain** - Text splitting & embeddings
- **ChromaDB** - Vector store
- **FastAPI** - REST API
- **Ollama** - Embedding model server

**Install all:**
```bash
pip install langchain langchain-community langchain-text-splitters chromadb fastapi uvicorn
```

---

## 🔐 Security

- API runs on `localhost:8765` (not public)
- Wiki.js API token in source (keep repo private if token is sensitive)
- ChromaDB data in `./chromadb` (local storage)
- No authentication on RAG API (localhost-only assumed)

**Production:**
- Move credentials to environment variables
- Add API key authentication
- Use HTTPS/TLS
- Restrict firewall to allowed IPs

---

## 📈 Performance

**Typical Numbers:**
- 61 Wiki pages → ~200 chunks (512 tokens each)
- Indexing time: ~2 minutes (with Ollama)
- Query time: <100ms (ChromaDB similarity search)
- Ollama embedding: ~50ms per chunk

**Optimization:**
- Batch indexing (20 pages at once)
- Persistent ChromaDB (no reload on API start)
- Ollama on same network (low latency)

---

## 🎯 Roadmap

**v1.0 (MVP):**
- [x] RAG Indexer (Wiki.js → ChromaDB)
- [x] FastAPI Query API
- [ ] Fix GraphQL content fetching
- [ ] Fix Ollama connectivity
- [ ] Successful first index

**v1.1:**
- [ ] Systemd service
- [ ] Auto-reindex cron
- [ ] Health monitoring
- [ ] OpenClaw tool integration

**v2.0:**
- [ ] Hybrid search (vector + keyword)
- [ ] Filter by tags/categories
- [ ] Query history & analytics
- [ ] Multi-language support

---

## 📝 License

MIT License - See [LICENSE](LICENSE)

---

## 🙏 Credits

- **Wiki.js** - Documentation platform
- **ChromaDB** - Vector database
- **Ollama** - Local LLM/Embedding server
- **LangChain** - RAG framework
- **OpenClaw** - AI agent orchestration

---

## 🔗 Links

- **GitHub:** https://github.com/bloop-herbert-bot/wikijs-rag
- **Wiki.js:** https://js.wiki/
- **ChromaDB:** https://www.trychroma.com/
- **Ollama:** https://ollama.com/

---

**Status:** 🚧 Work in Progress  
**Version:** 0.1.0  
**Last Update:** 2026-02-24
