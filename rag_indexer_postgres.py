#!/usr/bin/env python3
"""
Wiki.js PostgreSQL Direct Indexer
----------------------------------
Fetches pages directly from Wiki.js PostgreSQL database instead of GraphQL.

Based on: https://github.com/sks147/wikijs_rag
"""

import sys
import psycopg2
from typing import List, Dict
from datetime import datetime

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Configuration
POSTGRES_HOST = "192.168.0.252"  # Wiki.js container
POSTGRES_PORT = 5432
POSTGRES_DB = "wiki"
POSTGRES_USER = "wikijs"  # Default Wiki.js user
POSTGRES_PASSWORD = "wikijs"  # Need to get actual password

OLLAMA_BASE_URL = "http://192.168.0.204:11434"
CHROMA_PERSIST_DIR = "./chromadb"
COLLECTION_NAME = "wikijs"

# Chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def fetch_pages_from_postgres() -> List[Dict]:
    """Fetch all pages directly from PostgreSQL."""
    print("📡 Connecting to PostgreSQL...")
    
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Query pages table
        # Wiki.js stores pages in "pages" table with columns:
        # id, path, title, description, content, tags, etc.
        query = """
        SELECT id, path, title, description, content, 
               array_to_json(tags) as tags, "updatedAt"
        FROM pages
        WHERE content IS NOT NULL AND content != ''
        ORDER BY id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        pages = []
        for row in rows:
            pages.append({
                "id": row[0],
                "path": row[1],
                "title": row[2],
                "description": row[3] or "",
                "content": row[4],
                "tags": row[5] or [],
                "updatedAt": row[6].isoformat() if row[6] else ""
            })
        
        cursor.close()
        conn.close()
        
        print(f"✅ Fetched {len(pages)} pages from PostgreSQL")
        return pages
    
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        print("\nTry:")
        print("1. Check PostgreSQL is accessible from OpenClaw VM")
        print("2. Get correct credentials from Wiki.js container")
        print("3. Verify database name and table schema")
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
                    "tags": ",".join(page.get("tags", [])) if isinstance(page.get("tags"), list) else "",
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
    print("📚 Wiki.js RAG Indexer (PostgreSQL Direct)")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Fetch pages from PostgreSQL
    pages = fetch_pages_from_postgres()
    
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
