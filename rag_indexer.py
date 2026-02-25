#!/usr/bin/env python3
"""
Wiki.js RAG Indexer
-------------------
Fetches all Wiki.js pages via GraphQL, chunks them, generates embeddings,
and stores them in ChromaDB for semantic search.
"""

import requests
import json
import sys
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Configuration from environment variables
WIKI_API_URL = os.getenv("WIKI_API_URL", "http://localhost:3000/graphql")
WIKI_API_TOKEN = os.getenv("WIKI_API_TOKEN", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chromadb")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "wikijs")

# Chunking config
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))


def fetch_all_wiki_pages() -> List[Dict]:
    """Fetch all Wiki.js pages via GraphQL."""
    # Step 1: Get all page IDs
    query_list = """
    query {
      pages {
        list {
          id
          path
          title
          description
          updatedAt
        }
      }
    }
    """
    
    print("📡 Fetching Wiki.js page list...")
    
    try:
        response = requests.post(
            WIKI_API_URL,
            headers={
                "Authorization": f"Bearer {WIKI_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"query": query_list},
            timeout=30
        )
        
        # Debug: Print response
        if response.status_code != 200:
            print(f"   HTTP {response.status_code}: {response.text[:200]}")
        
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL Error: {data['errors']}")
            sys.exit(1)
        
        pages_meta = data["data"]["pages"]["list"]
        print(f"✅ Found {len(pages_meta)} pages")
        
        # Step 2: Fetch full content for each page
        print("📡 Fetching full page content...")
        pages_full = []
        
        for i, page_meta in enumerate(pages_meta):
            page_id = page_meta["id"]
            
            query_single = f"""
            query {{
              pages {{
                single(id: {page_id}) {{
                  id
                  path
                  title
                  content
                  description
                  tags {{
                    tag
                  }}
                  updatedAt
                }}
              }}
            }}
            """
            
            response = requests.post(
                WIKI_API_URL,
                headers={
                    "Authorization": f"Bearer {WIKI_API_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={"query": query_single},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and data["data"]["pages"]["single"]:
                    page_full = data["data"]["pages"]["single"]
                    pages_full.append(page_full)
                    print(f"   [{i+1}/{len(pages_meta)}] {page_full['path']}")
            else:
                print(f"   ⚠️ Failed to fetch page ID {page_id}")
        
        print(f"✅ Fetched {len(pages_full)} pages with content")
        return pages_full
    
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error: {e}")
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
                    "tags": ",".join([t["tag"] if isinstance(t, dict) else t for t in page.get("tags", [])]),
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
            model=OLLAMA_EMBEDDING_MODEL,
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
        
        # Add documents in batches (to avoid timeouts)
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
    print("📚 Wiki.js RAG Indexer")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Fetch pages
    pages = fetch_all_wiki_pages()
    
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
