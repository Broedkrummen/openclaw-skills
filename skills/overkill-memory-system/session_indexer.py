#!/usr/bin/env python3
"""
Session Indexer Module
Indexes old session files for searching
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# Paths
MEMORY_BASE = Path.home() / ".openclaw" / "memory"
SESSIONS_BASE = Path.home() / ".openclaw" / "sessions"
SESSION_INDEX_DIR = MEMORY_BASE / "session_index"
SESSION_INDEX_FILE = SESSION_INDEX_DIR / "index.json"


def get_sessions_path():
    """Get sessions directory path"""
    if SESSIONS_BASE.exists():
        return SESSIONS_BASE
    
    # Try alternative locations
    alt_paths = [
        Path.home() / ".openclaw" / "logs" / "sessions",
        Path.home() / ".openclaw" / "data" / "sessions",
    ]
    
    for p in alt_paths:
        if p.exists():
            return p
    
    return None


def index_sessions(force=False):
    """Index all .jsonl session files"""
    sessions_path = get_sessions_path()
    
    if sessions_path is None:
        print(f"No sessions directory found")
        return {"indexed": 0, "error": "No sessions directory"}
    
    # Create index directory
    SESSION_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing index
    existing_index = {}
    if SESSION_INDEX_FILE.exists() and not force:
        try:
            existing_index = json.loads(SESSION_INDEX_FILE.read_text())
        except Exception:
            existing_index = {}
    
    indexed_count = 0
    errors = []
    
    # Find all .jsonl files
    for jsonl_file in sessions_path.rglob("*.jsonl"):
        try:
            # Check if already indexed (by mtime)
            mtime = jsonl_file.stat().st_mtime
            file_key = str(jsonl_file.relative_to(sessions_path))
            
            if not force and file_key in existing_index:
                if existing_index[file_key].get("mtime") == mtime:
                    continue  # Skip unchanged files
            
            # Extract content from session file
            content = extract_session_content(jsonl_file)
            
            if content:
                # Extract metadata
                metadata = extract_session_metadata(jsonl_file, content)
                
                existing_index[file_key] = {
                    "path": str(jsonl_file),
                    "relative_path": file_key,
                    "mtime": mtime,
                    "size": jsonl_file.stat().st_size,
                    "message_count": metadata.get("message_count", 0),
                    "preview": content[:500] if content else "",
                    "first_message": metadata.get("first_message", ""),
                    "last_message": metadata.get("last_message", ""),
                    "indexed_at": datetime.now().isoformat()
                }
                indexed_count += 1
                
        except Exception as e:
            errors.append(f"{jsonl_file.name}: {str(e)}")
    
    # Save index
    SESSION_INDEX_FILE.write_text(json.dumps(existing_index, indent=2))
    
    result = {
        "indexed": indexed_count,
        "total_indexed": len(existing_index),
        "sessions_path": str(sessions_path),
    }
    
    if errors:
        result["errors"] = errors
    
    print(f"Indexed {indexed_count} new/updated sessions ({len(existing_index)} total)")
    return result


def extract_session_content(jsonl_file):
    """Extract text content from session file"""
    content_parts = []
    
    try:
        with open(jsonl_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                    # Extract text from different message formats
                    text = ""
                    if isinstance(msg, dict):
                        text = msg.get("content", "") or msg.get("text", "")
                    elif isinstance(msg, list):
                        # Sometimes it's a list of messages
                        for m in msg:
                            if isinstance(m, dict):
                                text += " " + (m.get("content", "") or m.get("text", ""))
                    else:
                        text = str(msg)
                    
                    if text:
                        content_parts.append(text)
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        return ""
    
    return " ".join(content_parts)


def extract_session_metadata(jsonl_file, content):
    """Extract metadata from session"""
    metadata = {
        "message_count": 0,
        "first_message": "",
        "last_message": ""
    }
    
    try:
        with open(jsonl_file) as f:
            lines = f.readlines()
            metadata["message_count"] = len([l for l in lines if l.strip()])
            
            # Get first message
            for line in lines:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        text = ""
                        if isinstance(msg, dict):
                            text = msg.get("content", "") or msg.get("text", "")
                        if text:
                            metadata["first_message"] = text[:200]
                            break
                    except:
                        continue
            
            # Get last message
            for line in reversed(lines):
                if line.strip():
                    try:
                        msg = json.loads(line)
                        text = ""
                        if isinstance(msg, dict):
                            text = msg.get("content", "") or msg.get("text", "")
                        if text:
                            metadata["last_message"] = text[:200]
                            break
                    except:
                        continue
                        
    except Exception:
        pass
    
    return metadata


def search_sessions(query, limit=10):
    """Search indexed sessions"""
    if not SESSION_INDEX_FILE.exists():
        # Try to auto-index first
        index_sessions()
    
    if not SESSION_INDEX_FILE.exists():
        return {"results": [], "error": "No index found"}
    
    try:
        index = json.loads(SESSION_INDEX_FILE.read_text())
    except Exception as e:
        return {"results": [], "error": str(e)}
    
    # Simple keyword search
    query_lower = query.lower()
    results = []
    
    for file_key, data in index.items():
        preview = data.get("preview", "").lower()
        first = data.get("first_message", "").lower()
        last = data.get("last_message", "").lower()
        
        # Calculate simple relevance score
        score = 0
        query_words = query_lower.split()
        
        for word in query_words:
            if word in preview:
                score += 3
            if word in first:
                score += 2
            if word in last:
                score += 2
        
        if score > 0:
            results.append({
                "path": data["path"],
                "relative_path": file_key,
                "score": score,
                "message_count": data.get("message_count", 0),
                "preview": data.get("preview", "")[:300],
                "first_message": data.get("first_message", ""),
                "last_message": data.get("last_message", ""),
                "indexed_at": data.get("indexed_at", "")
            })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": query,
        "results": results[:limit],
        "total_found": len(results)
    }


def clear_index():
    """Clear the session index"""
    if SESSION_INDEX_FILE.exists():
        SESSION_INDEX_FILE.unlink()
        print("Session index cleared")
    return {"cleared": True}


# CLI helpers
def cli_index_sessions(force=False):
    """CLI: Index sessions"""
    result = index_sessions(force=force)
    print(json.dumps(result, indent=2))
    return result


def cli_search_sessions(query, limit=10):
    """CLI: Search sessions"""
    result = search_sessions(query, limit=limit)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "index":
            force = "--force" in sys.argv
            cli_index_sessions(force=force)
        elif sys.argv[1] == "search":
            query = sys.argv[2] if len(sys.argv) > 2 else ""
            cli_search_sessions(query)
    else:
        print("Usage: session_indexer.py [index|search <query>]")
