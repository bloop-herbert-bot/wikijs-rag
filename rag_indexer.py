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
from datetime import datetime
from typing import List, Dict

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Configuration
WIKI_API_URL = "http://192.168.0.252:3000/graphql"
WIKI_API_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGkiOjQsImdycCI6MSwiaWF0IjoxNzcxOTQ4MTc2LCJleHAiOjE4NjY2MjA5NzYsImF1ZCI6InVybjp3aWtpLmpzIiwiaXNzIjoidXJuOndpa2kuanMifQ.IeqS7egEqjzi_h4BtOgrMBOI2Sj3nSQOmpb0rfqbBEe_-rr2_LHW7WbdRdFAzZLmrVfUxNUxAS2mqfWRutDzFRssTM1evQehATO88aiXybhGviy-ROa8phBTKgGf4okLEWw6ZPkqk7RoNZAyW_cGlTGG1ObcZXknZzfL8AGIqqcf_aNXDYzE4xLpp-J3I4Aek-hl3sDetd_Ch3e_4e-IIdy0n05M3ew7Q_ITh-iRj0rdDZRX5rphH7nG6lJXWBeca81ks1aKeL6GwBUWPO-R1YDjjfSchP_s8HU1_yIpA2eXyObKXSVIgmYOquF-B4Zf-OHufU9PQ-di-ojWHx_gRw"
OLLAMA_BASE_URL = "http://192.168.0.204:11434"  # Alternative: 192.168.10.24
CHROMA_PERSIST_DIR = "./chromadb"
COLLECTION_NAME = "wikijs"

# Chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


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
          tags
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
                  tags
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
