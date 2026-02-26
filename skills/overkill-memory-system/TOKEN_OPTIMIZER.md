# Framework: Token Memory Optimizer Integration

## Overview

Implemented token optimization features in overkill-memory-system:
- Reset & Summarize (manual consolidation)
- Session Indexing
- Hybrid Search (semantic + keyword)

---

## What It Does

| Feature | Description | Status |
|---------|-------------|--------|
| **Periodic Task Isolation** | Cron jobs in isolated sessions | ✅ Already supported |
| **Reset & Summarize** | Manual consolidation when >100k tokens | ✅ Implemented |
| **Hybrid Search** | Vector + keyword search | ✅ Implemented |
| **Session Indexing** | Index old conversations | ✅ Implemented |

---

## Implemented Features

### 1. reset_summarize.py

```bash
# Check token usage
overkill token-stats
# Output: Session tokens, message count, threshold status

# Dry run (preview)
overkill reset --dry-run

# Execute reset
overkill reset --confirm
```

Functions:
- `check_token_usage()` - Get session tokens
- `should_reset()` - Check if >100k tokens
- `reset_and_summarize(dry_run=False)` - Save facts, update MEMORY.md, daily log

Storage: `memory/reset_history.json`

### 2. session_indexer.py

```bash
# Index sessions
overkill index-sessions
overkill index-sessions --force  # Re-index all

# (Use in code)
session_indexer.search_sessions("query")
```

Functions:
- `index_sessions(force=False)` - Index all .jsonl files
- `search_sessions(query)` - Search indexed sessions

Storage: `memory/session_index/index.json`

### 3. hybrid_search.py

```bash
# Search with hybrid (semantic + keyword)
overkill search "query" --hybrid
```

Functions:
- `semantic_search(query)` - ChromaDB semantic search
- `keyword_search(query)` - Regex keyword search
- `hybrid_search(query)` - Combined with weighted ranking

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `token-stats` | Show current token usage |
| `reset --dry-run` | Preview what would be saved |
| `reset --confirm` | Execute reset & summarize |
| `index-sessions` | Index old session files |
| `search "query" --hybrid` | Hybrid semantic + keyword search |

---

## Memory Indexing

### Index Sessions

Sessions are indexed from `~/.openclaw/sessions/*.jsonl` (or fallback locations).

Each session file is parsed and indexed with:
- Message count
- Preview (first 500 chars)
- First/last message
- File mtime (for incremental updates)

### Search Sessions

Searches the index for keyword matches with scoring:
- Exact match in preview: +3 points
- Match in first/last message: +2 points

---

## Reset & Summarize Protocol

### Steps

1. **Check** session tokens (via `check_token_usage()`)
2. **Extract** facts/preferences/projects from SESSION-STATE.md
3. **Append** to MEMORY.md under timestamped section
4. **Update** today's daily log
5. **Log** to reset_history.json

### Thresholds

- **Reset threshold**: 100,000 tokens
- **Token estimation**: ~10 tokens per word from session content

---

## Usage Examples

```bash
# Check if you need to reset
overkill token-stats

# Preview reset (safe)
overkill reset --dry-run

# Actually reset when needed
overkill reset --confirm

# Index old sessions for searching
overkill index-sessions

# Search with hybrid mode
overkill search "python code" --hybrid

# Regular semantic search (default)
overkill search "python code"
```

---

## Files

- `reset_summarize.py` - Token reset & summarize logic
- `session_indexer.py` - Session file indexing
- `hybrid_search.py` - Combined semantic + keyword search

---

*Token Memory Optimizer integration - IMPLEMENTED*
