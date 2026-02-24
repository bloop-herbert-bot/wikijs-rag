#!/usr/bin/env python3
"""
Wiki.js SQLite Direct Indexer
------------------------------
Fetches pages directly from Wiki.js SQLite database instead of GraphQL.

Much simpler than PostgreSQL approach!
"""

import sys
import sqlite3
import json
from typing import List, Dict
from datetime import datetime

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Configuration
SQLITE_DB_PATH = "./db.sqlite"  # Local copy from Wiki.js container
OLLAMA_BASE_URL = "http://192.168.0.204:11434"
CHROMA_PERSIST_DIR = "./chromadb"
COLLECTION_NAME = "wikijs"

# Chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def fetch_pages_from_sqlite() -> List[Dict]:
    """Fetch all pages directly from SQLite database."""
    print("📡 Fetching pages from SQLite database...")
    print(f"   Database: {SQLITE_DB_PATH}")
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()
        
        # Query pages table
        # Wiki.js SQLite schema: pages table (no tags column!)
        query = """
        SELECT id, path, title, description, content, updatedAt
        FROM pages
        WHERE content IS NOT NULL AND content != ''
        ORDER BY id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        pages = []
        for row in rows:
            pages.append({
                "id": row["id"],
                "path": row["path"],
                "title": row["title"],
                "description": row["description"] or "",
                "content": row["content"],
                "tags": [],  # No tags in SQLite schema
                "updatedAt": row["updatedAt"] or ""
            })
        
        cursor.close()
        conn.close()
        
        print(f"✅ Fetched {len(pages)} pages from SQLite")
        return pages
    
    except sqlite3.Error as e:
        print(f"❌ SQLite Error: {e}")
        print("\nTry:")
        print("1. Copy database from Wiki.js container:")
        print(f"   sshpass -p 'fcdkxezn' scp root@192.168.0.252:{SQLITE_DB_PATH} ./db.sqlite")
        print("2. Then update SQLITE_DB_PATH = './db.sqlite'")
        sys.exit(1)


def chunk_pages(pages: List[Dict]) -> List[Document]:
    """Split pages into chunks with metadata."""
    print(f"\n✂️ Chunking {len(pages)} pages...")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    all_docs = []
    
    for page in pages:
        # Skip empty content
        if not page.get("content") or len(page["content"].strip()) < 50:
            continue
        
        # Create Document
        chunks = splitter.split_text(page["content"])
        
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "page_id": page["id"],
                    "path": page["path"],
                    "title": page["title"],
                    "description": page.get("description", ""),
                    "tags": ",".join(page.get("tags", [])),
                    "updated_at": page.get("updatedAt", ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            )
            all_docs.append(doc)
    
    print(f"✅ Created {len(all_docs)} chunks from {len(pages)} pages")
    return all_docs


def index_documents(documents: List[Document]) -> None:
    """Generate embeddings and store in ChromaDB."""
    print(f"\n🧠 Generating embeddings via Ollama ({OLLAMA_BASE_URL})...")
    
    try:
        # Init Ollama Embeddings
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=OLLAMA_BASE_URL
        )
        
        # Test connection
        print("   Testing Ollama connection...")
        test_embedding = embeddings.embed_query("test")
        print(f"   ✅ Ollama OK (embedding dim: {len(test_embedding)})")
        
        # Create/Load ChromaDB
        print(f"\n💾 Storing in ChromaDB ({CHROMA_PERSIST_DIR})...")
        
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        # Delete existing collection (fresh index)
        try:
            vectorstore.delete_collection()
            print("   🗑️ Deleted old collection")
        except:
            pass
        
        # Recreate
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        # Add documents in batches
        batch_size = 20
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            vectorstore.add_documents(batch)
            print(f"   📦 Indexed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        
        print(f"\n✅ Indexing complete!")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Documents: {len(documents)}")
        print(f"   Storage: {CHROMA_PERSIST_DIR}")
    
    except Exception as e:
        print(f"❌ Indexing failed: {e}")
        sys.exit(1)


def main():
    print("=" * 60)
    print("📚 Wiki.js RAG Indexer (SQLite Direct)")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Fetch pages from SQLite
    pages = fetch_pages_from_sqlite()
    
    # Step 2: Chunk pages
    documents = chunk_pages(pages)
    
    # Step 3: Index documents
    index_documents(documents)
    
    print()
    print("=" * 60)
    print("✅ RAG Index successfully created!")
    print("=" * 60)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
