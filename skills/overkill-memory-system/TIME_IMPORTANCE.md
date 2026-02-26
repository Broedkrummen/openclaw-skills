# Framework: Time-Based Search + Importance Ranking

## Overview

Add two new capabilities to overkill-memory-system:
1. **Time-Based Search** - Query memories by time range
2. **Importance Ranking** - Auto-rank memories by importance

---

## 1. Time-Based Search

### Concept

Search memories by time:
```bash
overkill search "project" --from 2026-01-01 --to 2026-02-01
overkill search "what did I think last week"
overkill timeline "project X"
```

### Implementation

```python
from datetime import datetime, timedelta
from pathlib import Path

class TimeSearch:
    def __init__(self):
        self.memory_path = Path("~/.openclaw/memory").expanduser()
    
    def search_by_time(self, query, from_date=None, to_date=None):
        """Search memories within time range"""
        results = []
        
        # Search daily files
        for md_file in self.memory_path.glob("*.md"):
            if from_date and md_file.stat().st_mtime < from_date.timestamp():
                continue
            if to_date and md_file.stat().st_mtime > to_date.timestamp():
                continue
            
            content = md_file.read_text()
            if query.lower() in content.lower():
                results.append({
                    "file": str(md_file),
                    "date": datetime.fromtimestamp(md_file.stat().st_mtime),
                    "snippet": extract_snippet(content, query)
                })
        
        return results
    
    def timeline(self, topic):
        """Show chronological timeline of topic"""
        results = []
        
        for md_file in sorted(self.memory_path.glob("*.md")):
            content = md_file.read_text()
            if topic.lower() in content.lower():
                results.append({
                    "date": md_file.name.replace(".md", ""),
                    "file": str(md_file)
                })
        
        return sorted(results, key=lambda x: x["date"])
    
    def natural_time(self, query):
        """Parse natural time like 'last week', 'yesterday'"""
        now = datetime.now()
        
        if "yesterday" in query:
            return (now - timedelta(days=1), now)
        elif "last week" in query:
            return (now - timedelta(weeks=1), now)
        elif "last month" in query:
            return (now - timedelta(days=30), now)
        else:
            return None
```

### CLI Commands

```bash
# Search by date range
overkill search "project" --from 2026-01-01 --to 2026-02-01

# Natural time
overkill search "what did I think last week"

# Timeline
overkill timeline "project X"

# Recent memories
overkill recent --days 7
```

---

## 2. Importance Ranking

### Concept

Auto-rank memories by importance based on:
- Frequency of mention
- User corrections
- Emotional weight
- Recency

### Implementation

```python
class ImportanceRanker:
    def __init__(self):
        self.weights = {
            "frequency": 0.3,
            "correction": 0.25,
            "emotional": 0.25,
            "recency": 0.2
        }
    
    def calculate_importance(self, memory):
        """Calculate importance score 0-1"""
        score = 0.0
        
        # Frequency (0-0.3)
        freq = self._count_mentions(memory["content"])
        score += min(freq / 10, 1.0) * self.weights["frequency"]
        
        # Correction boost (0-0.25)
        if memory.get("was_corrected"):
            score += 0.25
        
        # Emotional weight (0-0.25)
        emotions = memory.get("emotions", [])
        score += len(emotions) / 5 * self.weights["emotional"]
        
        # Recency (0-0.2)
        age_days = (datetime.now() - memory["date"]).days
        score += max(0, 1 - age_days / 365) * self.weights["recency"]
        
        return min(score, 1.0)
    
    def rank_by_importance(self, memories):
        """Sort memories by importance"""
        for mem in memories:
            mem["importance"] = self.calculate_importance(mem)
        
        return sorted(memories, key=lambda x: x["importance"], reverse=True)
    
    def top_memories(self, limit=10):
        """Get most important memories"""
        all_memories = self._load_all_memories()
        ranked = self.rank_by_importance(all_memories)
        return ranked[:limit]
```

### CLI Commands

```bash
# Show important memories
overkill important --limit 10

# Show what matters most
overkill priority --days 30

# Importance stats
overkill importance-stats
```

---

## Combined: Time + Importance

```python
def search_with_time_and_importance(query, from_date=None, to_date=None, 
                                     min_importance=0.0):
    """Search with both time and importance filtering"""
    
    # Step 1: Time-based search
    results = time_search.search_by_time(query, from_date, to_date)
    
    # Step 2: Rank by importance
    ranked = importance_ranker.rank_by_importance(results)
    
    # Step 3: Filter by minimum importance
    return [r for r in ranked if r["importance"] >= min_importance]
```

### CLI

```bash
# Important memories from last month
overkill search "project" --from 2026-01-01 --min-importance 0.7

# Top memories this week
overkill important --days 7
```

---

## Summary

| Feature | CLI Command |
|---------|------------|
| Time search | `search --from --to` |
| Natural time | `search "last week"` |
| Timeline | `timeline <topic>` |
| Importance rank | `important --limit` |
| Priority | `priority --days` |
| Combined | `search --min-importance` |

---

*Time-Based Search + Importance Ranking Framework*
