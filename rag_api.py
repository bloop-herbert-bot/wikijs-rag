#!/usr/bin/env python3
"""
Wiki.js RAG Query API
---------------------
FastAPI service for semantic search over Wiki.js documentation.
Accessible by all OpenClaw agents.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import sys

# LangChain imports
try:
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.vectorstores import Chroma
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install fastapi uvicorn langchain langchain-community chromadb")
    sys.exit(1)

# Configuration
OLLAMA_BASE_URL = "http://192.168.0.118:11434"
CHROMA_PERSIST_DIR = "./chromadb"
COLLECTION_NAME = "wikijs"

# FastAPI App
app = FastAPI(
    title="Wiki.js RAG API",
    description="Semantic search API for Wiki.js documentation",
    version="1.0.0"
)

# Global vectorstore (loaded on startup)
vectorstore = None
embeddings = None


@app.on_event("startup")
async def startup_event():
    """Initialize ChromaDB and embeddings on startup."""
    global vectorstore, embeddings
    
    print("🚀 Starting Wiki.js RAG API...")
    
    try:
        # Init Ollama Embeddings
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=OLLAMA_BASE_URL
        )
        
        # Load ChromaDB
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        # Test query
        test_results = vectorstore.similarity_search("test", k=1)
        doc_count = len(vectorstore.get()["ids"])
        
        print(f"✅ ChromaDB loaded successfully")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Documents: {doc_count}")
        print(f"   Storage: {CHROMA_PERSIST_DIR}")
    
    except Exception as e:
        print(f"❌ Failed to load ChromaDB: {e}")
        sys.exit(1)


# Request/Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query", min_length=3)
    top_k: int = Field(5, description="Number of results to return", ge=1, le=20)
    filter_path: Optional[str] = Field(None, description="Filter by page path (e.g., 'de/Container')")


class QueryResult(BaseModel):
    content: str
    metadata: Dict
    score: float


class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]
    count: int


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "Wiki.js RAG API",
        "version": "1.0.0",
        "endpoints": {
            "/query": "POST - Semantic search query",
            "/health": "GET - Health check",
            "/stats": "GET - Collection statistics"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    if vectorstore is None:
        raise HTTPException(status_code=503, detail="Vectorstore not initialized")
    
    try:
        doc_count = len(vectorstore.get()["ids"])
        return {
            "status": "ok",
            "collection": COLLECTION_NAME,
            "documents": doc_count,
            "ollama": OLLAMA_BASE_URL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/stats")
async def stats():
    """Get collection statistics."""
    if vectorstore is None:
        raise HTTPException(status_code=503, detail="Vectorstore not initialized")
    
    try:
        data = vectorstore.get()
        doc_count = len(data["ids"])
        
        # Count unique pages
        unique_pages = set()
        for metadata in data["metadatas"]:
            if "page_id" in metadata:
                unique_pages.add(metadata["page_id"])
        
        return {
            "collection": COLLECTION_NAME,
            "total_chunks": doc_count,
            "unique_pages": len(unique_pages),
            "storage": CHROMA_PERSIST_DIR
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_wiki(request: QueryRequest):
    """
    Semantic search over Wiki.js documentation.
    
    Example:
        POST /query
        {
          "query": "Was ist die IP von ioBroker?",
          "top_k": 3
        }
    """
    if vectorstore is None:
        raise HTTPException(status_code=503, detail="Vectorstore not initialized")
    
    try:
        # Optional path filter
        filter_dict = None
        if request.filter_path:
            filter_dict = {"path": {"$regex": f"^{request.filter_path}"}}
        
        # Similarity search with scores
        results = vectorstore.similarity_search_with_score(
            request.query,
            k=request.top_k,
            filter=filter_dict
        )
        
        # Format results
        query_results = [
            QueryResult(
                content=doc.page_content,
                metadata=doc.metadata,
                score=float(score)
            )
            for doc, score in results
        ]
        
        return QueryResponse(
            query=request.query,
            results=query_results,
            count=len(query_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Development mode
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, reload=True)
