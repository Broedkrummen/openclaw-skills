# Framework: Link Tracker

## Overview

Track and remember URLs visited/bookmarked for quick recall.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Add links** | Save URLs with titles and tags |
| **Search** | Find links by title/tag |
| **Visit tracking** | Remember when you visited |
| **Categories** | Organize by topic |

---

## Implementation

```python
import json
from pathlib import Path
from datetime import datetime

class LinkTracker:
    def __init__(self):
        self.links_file = Path("~/.openclaw/memory/links.json")
        self.links = self._load()
    
    def _load(self):
        if self.links_file.exists():
            return json.loads(self.links_file.read_text())
        return {"links": []}
    
    def _save(self):
        self.links_file.write_text(json.dumps(self.links, indent=2))
    
    def add(self, url, title=None, tags=None):
        link = {
            "id": len(self.links["links"]) + 1,
            "url": url,
            "title": title or url,
            "tags": tags or [],
            "created": datetime.now().isoformat(),
            "visits": 0
        }
        self.links["links"].append(link)
        self._save()
        return link
    
    def search(self, query):
        results = []
        for link in self.links["links"]:
            if (query.lower() in link["url"].lower() or
                query.lower() in link["title"].lower() or
                any(query.lower() in tag.lower() for tag in link["tags"])):
                results.append(link)
        return results
    
    def visit(self, link_id):
        for link in self.links["links"]:
            if link["id"] == link_id:
                link["visits"] += 1
                link["last_visited"] = datetime.now().isoformat()
                self._save()
                return link
    
    def list(self, limit=10):
        return sorted(self.links["links"], 
                     key=lambda x: x.get("visits", 0), 
                     reverse=True)[:limit]
```

---

## CLI Commands

```bash
# Add link
overkill link add "https://example.com" --title "Example" --tags "docs,reference"

# Search links
overkill link search "python"

# Visit (mark as visited)
overkill link visit 1

# Top links
overkill link top

# List all
overkill link list
```

---

## Storage

```json
{
  "links": [
    {
      "id": 1,
      "url": "https://docs.python.org",
      "title": "Python Docs",
      "tags": ["docs", "reference"],
      "created": "2026-02-25T10:00:00Z",
      "visits": 5,
      "last_visited": "2026-02-25T12:00:00Z"
    }
  ]
}
```

---

*Link Tracker Framework*
