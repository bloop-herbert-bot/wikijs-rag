#!/bin/bash
# sync_wikijs.sh - Auto-Reindex Wiki.js Content
# 
# Usage: ./sync_wikijs.sh
# Cron: 0 2 * * * /path/to/sync_wikijs.sh >> /tmp/rag_reindex.log 2>&1

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Wiki.js RAG Sync Started: $(date)"
echo "========================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: venv not found! Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if indexer exists
if [ ! -f "rag_indexer.py" ]; then
    echo "❌ Error: rag_indexer.py not found!"
    exit 1
fi

# Run indexer
echo "📥 Fetching Wiki.js pages via GraphQL..."
echo "🧠 Generating embeddings and updating ChromaDB..."
python3 -u rag_indexer.py

if [ $? -eq 0 ]; then
    echo "✅ Reindexing successful!"
    echo "📊 Stats:"
    curl -s http://localhost:${API_PORT:-8765}/stats 2>/dev/null | grep -o '"total_chunks":[0-9]*' || echo "   (API not running)"
else
    echo "❌ Reindexing failed!"
    exit 1
fi

# Optional: Restart API if running as systemd service
# Uncomment if you use systemd:
# if systemctl is-active --quiet wikijs-rag; then
#     echo "🔄 Restarting RAG API service..."
#     sudo systemctl restart wikijs-rag
# fi

echo "========================================="
echo "Wiki.js RAG Sync Completed: $(date)"
echo "========================================="
