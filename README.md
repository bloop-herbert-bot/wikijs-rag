# Wiki.js RAG System

**Semantic search API for Wiki.js documentation** - Enables AI agents and applications to query Wiki.js content using natural language.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 Features

- **Semantic Search:** Query Wiki.js pages with natural language
- **ChromaDB Vector Store:** Efficient similarity search over embedded content
- **Ollama Embeddings:** Uses `nomic-embed-text` model (or any Ollama embedding model)
- **FastAPI REST API:** Simple HTTP interface for all applications
- **Generic & Configurable:** No hardcoded credentials - all via environment variables

---

## 🏗️ Architecture

```
Wiki.js (Database)
    ↓ GraphQL API
RAG Indexer (Python)
    ↓ Chunks + Embeddings
ChromaDB Vector Store
    ↓ Similarity Search
FastAPI Query API
    ↓ HTTP/JSON
Your Application / AI Agent
```

---

## 📦 Installation

### 1. Prerequisites

- **Python 3.11+**
- **Wiki.js instance** with GraphQL API enabled
- **Ollama** with `nomic-embed-text` model installed

Install Ollama model:
```bash
ollama pull nomic-embed-text
```

### 2. Clone Repository

```bash
git clone https://github.com/bloop-herbert-bot/wikijs-rag.git
cd wikijs-rag
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
nano .env
```

**Required settings:**
```env
# Wiki.js Configuration
WIKI_API_URL=http://your-wikijs-host:3000/graphql
WIKI_API_TOKEN=your_api_token_here

# Ollama Configuration
OLLAMA_BASE_URL=http://your-ollama-host:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ChromaDB Configuration (defaults are fine for most cases)
CHROMA_PERSIST_DIR=./chromadb
COLLECTION_NAME=wikijs

# API Configuration
API_HOST=0.0.0.0
API_PORT=8765
```

**Getting Wiki.js API Token:**
1. Log into Wiki.js as admin
2. Go to **Administration → API Access**
3. Create new API key with **Read** permissions
4. Copy the token to `.env`

### 5. Run Indexer (First Time)

```bash
python3 rag_indexer.py
```

Expected output:
```
📚 Wiki.js RAG Indexer
============================================================
📡 Fetching Wiki.js page list...
✅ Found 61 pages
📡 Fetching full page content...
✂️ Chunking 61 pages...
✅ Created 1288 chunks from 61 pages
🧠 Generating embeddings via Ollama...
✅ Ollama OK (embedding dim: 768)
💾 Storing in ChromaDB...
📦 Indexed batch 1/65
...
✅ Indexing complete!
   Collection: wikijs
   Documents: 1288
```

### 6. Start API Server

```bash
python3 rag_api.py
```

Or with uvicorn:
```bash
uvicorn rag_api:app --host 0.0.0.0 --port 8765
```

API is now running at `http://localhost:8765`

---

## 🚀 Usage

### Query API

**Endpoint:** `POST /query`

**Request:**
```json
{
  "query": "How do I configure authentication?",
  "top_k": 3
}
```

**Response:**
```json
{
  "query": "How do I configure authentication?",
  "count": 3,
  "results": [
    {
      "content": "To configure LDAP authentication in Wiki.js...",
      "metadata": {
        "page_id": 42,
        "path": "admin/authentication",
        "title": "Authentication Configuration"
      },
      "score": 0.89
    }
  ]
}
```

### cURL Example

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I backup my wiki?",
    "top_k": 5
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8765/query",
    json={"query": "Docker installation guide", "top_k": 3}
)

results = response.json()
for result in results["results"]:
    print(f"📄 {result['metadata']['title']}")
    print(f"   {result['content'][:100]}...")
    print(f"   Score: {result['score']:.2f}\n")
```

### OpenClaw Integration

Add to your OpenClaw agent:

```python
# Query Wiki.js RAG
def query_wiki(question: str) -> str:
    import requests
    resp = requests.post(
        "http://localhost:8765/query",
        json={"query": question, "top_k": 3}
    )
    results = resp.json()["results"]
    return "\n\n".join([r["content"] for r in results])
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/stats` | GET | Collection statistics |
| `/query` | POST | Semantic search |

### Health Check

```bash
curl http://localhost:8765/health
```

Response:
```json
{
  "status": "ok",
  "collection": "wikijs",
  "documents": 1288
}
```

---

## 🔄 Auto-Reindexing

Keep ChromaDB synchronized with Wiki.js automatically.

### Quick Setup

**1. Test the sync script:**
```bash
./sync_wikijs.sh
```

**2. Schedule with cron:**
```bash
crontab -e
# Add: 0 2 * * * /path/to/wikijs-rag/sync_wikijs.sh >> /tmp/rag_reindex.log 2>&1
```

**3. Or use OpenClaw cron:**
```bash
openclaw cron add --name "Wiki.js RAG Sync" --schedule "0 2 * * *" \
  --command "/path/to/wikijs-rag/sync_wikijs.sh"
```

**📚 Full guide:** See [AUTO_REINDEX.md](AUTO_REINDEX.md) for detailed setup, monitoring, and troubleshooting.

### Manual Reindex

Run indexer directly:
```bash
python3 rag_indexer.py
```

---

## 🔧 Production Deployment

### Systemd Service (API)

Create `/etc/systemd/system/wikijs-rag.service`:

```ini
[Unit]
Description=Wiki.js RAG Query API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/wikijs-rag
EnvironmentFile=/path/to/wikijs-rag/.env
ExecStart=/path/to/wikijs-rag/venv/bin/uvicorn rag_api:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl enable wikijs-rag
sudo systemctl start wikijs-rag
sudo systemctl status wikijs-rag
```

### Docker Deployment

`Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "rag_api:app", "--host", "0.0.0.0", "--port", "8765"]
```

`docker-compose.yml`:
```yaml
version: '3.8'
services:
  wikijs-rag:
    build: .
    ports:
      - "8765:8765"
    env_file:
      - .env
    volumes:
      - ./chromadb:/app/chromadb
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Ollama Connection Failed

**Error:**
```
Failed to establish connection to http://localhost:11434
```

**Solution:**
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify `nomic-embed-text` model exists: `ollama list`
3. Install if missing: `ollama pull nomic-embed-text`
4. Check firewall/network between RAG system and Ollama

### Wiki.js GraphQL Error

**Error:**
```
Field "tags" must not have a selection since type "[String]" has no subfields
```

**Solution:**
- This is fixed in the latest version
- GraphQL schema expects `tags { tag }` for `single` queries
- But `tags` (without subfields) for `list` queries

### No Pages Fetched

**Error:**
```
✅ Found 61 pages
✅ Fetched 0 pages with content
```

**Solution:**
1. Check API token has **read** permissions in Wiki.js
2. Verify Wiki.js GraphQL endpoint is accessible
3. Run with debug: `python3 -u rag_indexer.py`

### ChromaDB Permission Error

**Error:**
```
PermissionError: [Errno 13] Permission denied: './chromadb'
```

**Solution:**
```bash
chmod -R 755 ./chromadb
# Or delete and recreate:
rm -rf ./chromadb
python3 rag_indexer.py
```

---

## ⚙️ Configuration Options

### Chunking Settings

Adjust in `.env`:
```env
CHUNK_SIZE=512          # Characters per chunk
CHUNK_OVERLAP=50        # Overlap between chunks
```

**Smaller chunks:** More precise, more embeddings  
**Larger chunks:** More context, fewer embeddings

### Embedding Model

Any Ollama embedding model works:
```env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text    # Default (fast)
# OLLAMA_EMBEDDING_MODEL=mxbai-embed-large  # Better quality
# OLLAMA_EMBEDDING_MODEL=all-minilm         # Faster
```

List available models:
```bash
ollama list | grep embed
```

---

## 📚 Dependencies

- **Python 3.11+**
- **LangChain** - Text splitting & embeddings framework
- **ChromaDB** - Vector database
- **FastAPI** - REST API framework
- **Ollama** - Embedding model server
- **python-dotenv** - Environment variable management

Install all:
```bash
pip install -r requirements.txt
```

---

## 🔐 Security Notes

- **API Token:** Keep `.env` secure and out of version control (already in `.gitignore`)
- **API Authentication:** The RAG API has no built-in auth - use a reverse proxy (nginx/traefik) if exposing publicly
- **Network:** Run on localhost or private network by default
- **HTTPS:** Use a reverse proxy for TLS if internet-facing

**Production checklist:**
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Run API behind reverse proxy with auth
- [ ] Use firewall to restrict access
- [ ] Regular security updates: `pip install --upgrade -r requirements.txt`

---

## 📈 Performance

**Typical Numbers:**
- 100 Wiki pages → ~1000-2000 chunks (depending on content size)
- Indexing time: ~2-5 minutes (depends on Ollama speed)
- Query time: <100ms (ChromaDB similarity search)
- Ollama embedding: ~30-100ms per chunk (GPU accelerated)

**Optimization Tips:**
- Use GPU-accelerated Ollama for faster embeddings
- Increase `batch_size` in `rag_indexer.py` for faster indexing
- Use SSD for ChromaDB storage (`CHROMA_PERSIST_DIR`)
- Run Ollama on same machine/network as RAG system

---

## 🎯 Roadmap

- [x] Basic RAG indexer (Wiki.js → ChromaDB)
- [x] FastAPI query API
- [x] Environment variable configuration
- [x] Fixed GraphQL schema issues
- [x] Updated to latest LangChain packages
- [ ] Query filtering by tags/categories
- [ ] Hybrid search (vector + keyword)
- [ ] Multi-language support
- [ ] Query history & analytics
- [ ] Web UI for testing queries

---

## 🔌 OpenClaw Integration

**Native agent tool for semantic Wiki.js search**

### Quick Setup

1. **Copy plugin to OpenClaw:**
   ```bash
   cp -r openclaw-plugin ~/.openclaw/plugins/wikijs-search
   ```

2. **Enable plugin in OpenClaw config:**
   ```bash
   # Edit ~/.openclaw/openclaw.json
   {
     "plugins": {
       "installed": ["wikijs-search"]
     }
   }
   ```

3. **Restart OpenClaw:**
   ```bash
   openclaw gateway restart
   ```

### Usage in Agents

The `wikijs_search` tool is automatically available:

```
User: What is the IP address of ioBroker?

Agent: Let me search the documentation...
[calls wikijs_search({query: "ioBroker IP address", top_k: 3})]

According to Container/iobroker page, ioBroker runs on 192.168.0.110.
```

**Tool Parameters:**
- `query` (string, required): Natural language search query
- `top_k` (number, optional, default 3): Number of results (1-10)
- `filter_path` (string, optional): Filter by Wiki.js path prefix

**Optional Health Check:**

Enable `wikijs_health` tool in agent config for API status monitoring:
```json
{
  "agents": {
    "list": [{
      "id": "main",
      "tools": {
        "allow": ["wikijs_health"]
      }
    }]
  }
}
```

See `openclaw-plugin/README.md` for detailed documentation.

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📝 License

MIT License - See [LICENSE](LICENSE)

---

## 🙏 Credits

- **Wiki.js** - Open-source documentation platform
- **ChromaDB** - Embeddable vector database
- **Ollama** - Local LLM/Embedding server
- **LangChain** - RAG & AI framework
- **FastAPI** - Modern Python web framework

---

## 🔗 Links

- **GitHub:** https://github.com/bloop-herbert-bot/wikijs-rag
- **Wiki.js:** https://js.wiki/
- **ChromaDB:** https://www.trychroma.com/
- **Ollama:** https://ollama.com/
- **LangChain:** https://python.langchain.com/

---

**Made with ❤️ for the Wiki.js & AI community**
