#!/usr/bin/env python3
"""
Hybrid Search Module
Combines semantic search with keyword search
"""

import json
import re
from pathlib import Path

# Import optional dependencies
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Paths
MEMORY_BASE = Path.home() / ".openclaw" / "memory"
CHROMA_DIR = MEMORY_BASE / "chroma"
CHROMA_CODY = MEMORY_BASE / "chroma_cody"


def semantic_search(query, limit=10, collection=None):
    """
    Perform semantic search using ChromaDB
    Returns list of results with content and scores
    """
    if not CHROMADB_AVAILABLE:
        return {
            "results": [],
            "method": "semantic",
            "error": "ChromaDB not available"
        }
    
    # Try default collections
    collections_to_try = []
    
    if collection:
        collections_to_try.append(collection)
    else:
        # Try common collection names
        if CHROMA_DIR.exists():
            collections_to_try.extend(["memory", "default", "cody"])
        if CHROMA_CODY.exists():
            collections_to_try.append("cody")
    
    for col_name in collections_to_try:
        try:
            client = chromadb.PersistentClient(path=str(CHROMA_DIR if CHROMA_DIR.exists() else CHROMA_CODY))
            collection = client.get_collection(name=col_name)
            
            results = collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            parsed_results = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    parsed_results.append({
                        "content": doc,
                        "id": results["ids"][0][i] if results.get("ids") else None,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "collection": col_name
                    })
            
            return {
                "results": parsed_results,
                "method": "semantic",
                "collection": col_name,
                "query": query
            }
            
        except Exception as e:
            continue
    
    return {
        "results": [],
        "method": "semantic",
        "error": "No valid collections found"
    }


def keyword_search(query, limit=10, search_paths=None):
    """
    Perform keyword search using regex
    Searches through memory files
    """
    if search_paths is None:
        search_paths = [
            MEMORY_BASE / "MEMORY.md",
            MEMORY_BASE / "daily",
        ]
    
    query_lower = query.lower()
    query_words = query_lower.split()
    
    # Build regex pattern - match any query word
    pattern = re.compile(r'\b(' + '|'.join(re.escape(w) for w in query_words) + r')\b', re.IGNORECASE)
    
    results = []
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob("*.md")) + list(search_path.rglob("*.txt"))
        
        for file_path in files:
            try:
                content = file_path.read_text(errors='ignore')
                
                # Find matches
                matches = pattern.findall(content)
                if matches:
                    # Calculate score based on number of matches
                    score = len(matches)
                    
                    # Get context around first match
                    match_start = pattern.search(content)
                    if match_start:
                        start = max(0, match_start.start() - 100)
                        end = min(len(content), match_start.end() + 200)
                        preview = content[start:end].strip()
                    else:
                        preview = content[:300].strip()
                    
                    results.append({
                        "file": str(file_path.relative_to(MEMORY_BASE)),
                        "absolute_path": str(file_path),
                        "score": score,
                        "preview": preview,
                        "matches": len(matches)
                    })
                    
            except Exception as e:
                continue
    
    # Sort by score and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "results": results[:limit],
        "method": "keyword",
        "query": query,
        "files_searched": len(results)
    }


def hybrid_search(query, limit=10, semantic_weight=0.6, keyword_weight=0.4):
    """
    Combine semantic and keyword search results
    Uses weighted ranking
    """
    # Run both searches in parallel
    sem_results = semantic_search(query, limit=limit * 2)
    kw_results = keyword_search(query, limit=limit * 2)
    
    # Normalize and combine scores
    combined = {}
    
    # Process semantic results
    if sem_results.get("results"):
        max_sem_score = max(r.get("distance", 1) or 1 for r in sem_results["results"])
        for r in sem_results["results"]:
            key = r.get("id") or r.get("content", "")[:50]
            # Convert distance to similarity (lower distance = higher similarity)
            similarity = 1 - (r.get("distance", 1) or 1) / max_sem_score if max_sem_score > 0 else 0
            combined[key] = {
                "content": r.get("content", ""),
                "source": "semantic",
                "semantic_score": similarity,
                "keyword_score": 0,
                "total_score": similarity * semantic_weight
            }
    
    # Process keyword results
    if kw_results.get("results"):
        max_kw_score = max(r.get("score", 1) for r in kw_results["results"]) or 1
        for r in kw_results["results"]:
            key = r.get("file") + ":" + r.get("preview", "")[:50]
            normalized_score = r.get("score", 1) / max_kw_score
            
            if key in combined:
                combined[key]["keyword_score"] = normalized_score
                combined[key]["total_score"] = (
                    combined[key]["semantic_score"] * semantic_weight +
                    normalized_score * keyword_weight
                )
                combined[key]["source"] = "hybrid"
            else:
                combined[key] = {
                    "content": r.get("preview", ""),
                    "file": r.get("file", ""),
                    "source": "keyword",
                    "semantic_score": 0,
                    "keyword_score": normalized_score,
                    "total_score": normalized_score * keyword_weight
                }
    
    # Sort by combined score
    final_results = sorted(
        combined.values(),
        key=lambda x: x["total_score"],
        reverse=True
    )[:limit]
    
    return {
        "results": final_results,
        "method": "hybrid",
        "query": query,
        "semantic_results": len(sem_results.get("results", [])),
        "keyword_results": len(kw_results.get("results", [])),
        "weights": {
            "semantic": semantic_weight,
            "keyword": keyword_weight
        }
    }


def search(query, use_hybrid=False, limit=10):
    """
    Unified search interface
    use_hybrid=True uses combined semantic + keyword search
    """
    if use_hybrid:
        return hybrid_search(query, limit=limit)
    else:
        # Default to semantic
        return semantic_search(query, limit=limit)


# CLI helpers
def cli_semantic_search(query, limit=10):
    """CLI: Semantic search"""
    result = semantic_search(query, limit=limit)
    print(json.dumps(result, indent=2))
    return result


def cli_keyword_search(query, limit=10):
    """CLI: Keyword search"""
    result = keyword_search(query, limit=limit)
    print(json.dumps(result, indent=2))
    return result


def cli_hybrid_search(query, limit=10):
    """CLI: Hybrid search"""
    result = hybrid_search(query, limit=limit)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = sys.argv[1] if len(sys.argv) > 1 else ""
        method = sys.argv[2] if len(sys.argv) > 2 else "semantic"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        if method == "semantic":
            cli_semantic_search(query, limit)
        elif method == "keyword":
            cli_keyword_search(query, limit)
        elif method == "hybrid":
            cli_hybrid_search(query, limit)
    else:
        print("Usage: hybrid_search.py <query> [semantic|keyword|hybrid] [limit]")
