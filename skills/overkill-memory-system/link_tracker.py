#!/usr/bin/env python3
"""
Link Tracker - Save and recall URLs with titles and tags.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse


class LinkTracker:
    def __init__(self, memory_path=None):
        self.memory_path = Path(memory_path or os.path.expanduser("~/.openclaw/memory"))
        self.links_file = self.memory_path / "links.json"
        self.links = self._load()
    
    def _load(self):
        """Load links from storage file."""
        if self.links_file.exists():
            try:
                return json.loads(self.links_file.read_text())
            except (json.JSONDecodeError, OSError, PermissionError):
                return {"links": [], "last_id": 0}
        return {"links": [], "last_id": 0}
    
    def _save(self):
        """Save links to storage file."""
        self.links_file.write_text(json.dumps(self.links, indent=2))
    
    def _get_next_id(self):
        """Get next available link ID."""
        return self.links.get("last_id", 0) + 1
    
    def add(self, url, title=None, tags=None):
        """Add a new link with optional title and tags."""
        if not url:
            raise ValueError("URL is required")
        
        # Auto-generate title from URL if not provided
        if not title:
            parsed = urlparse(url)
            title = parsed.netloc or url
        
        link = {
            "id": self._get_next_id(),
            "url": url,
            "title": title,
            "tags": [t.strip() for t in (tags or [])],
            "created": datetime.now().isoformat(),
            "visits": 0,
            "last_visited": None
        }
        
        self.links["links"].append(link)
        self.links["last_id"] = link["id"]
        self._save()
        
        return link
    
    def search(self, query):
        """Search links by URL, title, or tags."""
        if not query:
            return self.list(limit=20)
        
        query_lower = query.lower()
        results = []
        
        for link in self.links["links"]:
            # Check URL
            if query_lower in link["url"].lower():
                results.append(link)
                continue
            
            # Check title
            if query_lower in link["title"].lower():
                results.append(link)
                continue
            
            # Check tags
            if any(query_lower in tag.lower() for tag in link.get("tags", [])):
                results.append(link)
                continue
        
        return results
    
    def visit(self, link_id):
        """Mark a link as visited (increment visit count)."""
        try:
            link_id = int(link_id)
        except (ValueError, TypeError):
            return {"error": "Invalid link ID"}
        
        for link in self.links["links"]:
            if link["id"] == link_id:
                link["visits"] = link.get("visits", 0) + 1
                link["last_visited"] = datetime.now().isoformat()
                self._save()
                return link
        
        return {"error": f"Link {link_id} not found"}
    
    def delete(self, link_id):
        """Delete a link by ID."""
        try:
            link_id = int(link_id)
        except (ValueError, TypeError):
            return {"error": "Invalid link ID"}
        
        original_len = len(self.links["links"])
        self.links["links"] = [l for l in self.links["links"] if l["id"] != link_id]
        
        if len(self.links["links"]) < original_len:
            self._save()
            return {"deleted": link_id}
        
        return {"error": f"Link {link_id} not found"}
    
    def list(self, limit=10, sort_by="recent"):
        """List links, optionally sorted."""
        links = self.links["links"].copy()
        
        if sort_by == "visits":
            links.sort(key=lambda x: x.get("visits", 0), reverse=True)
        elif sort_by == "title":
            links.sort(key=lambda x: x.get("title", "").lower())
        else:  # recent
            links.sort(key=lambda x: x.get("created", ""), reverse=True)
        
        return links[:limit]
    
    def top(self, limit=10):
        """Get most visited links."""
        return self.list(limit=limit, sort_by="visits")
    
    def get(self, link_id):
        """Get a specific link by ID."""
        try:
            link_id = int(link_id)
        except (ValueError, TypeError):
            return {"error": "Invalid link ID"}
        
        for link in self.links["links"]:
            if link["id"] == link_id:
                return link
        
        return {"error": f"Link {link_id} not found"}
    
    def stats(self):
        """Get link statistics."""
        links = self.links["links"]
        total_visits = sum(l.get("visits", 0) for l in links)
        
        # Count tags
        all_tags = []
        for link in links:
            all_tags.extend(link.get("tags", []))
        from collections import Counter
        tag_counts = Counter(all_tags)
        
        return {
            "total_links": len(links),
            "total_visits": total_visits,
            "unique_tags": len(tag_counts),
            "top_tags": dict(tag_counts.most_common(10))
        }
    
    def format_list(self, links=None, limit=10):
        """Format links as a readable string."""
        if links is None:
            links = self.list(limit=limit)
        
        if not links:
            return "No links saved yet. Use: link add <url> [--title \"...\"] [--tags tag1,tag2]"
        
        lines = ["📋 Your Links:", ""]
        
        for link in links:
            visit_info = f" ({link.get('visits', 0)} visits)" if link.get('visits', 0) > 0 else ""
            lines.append(f"  [{link['id']}] {link['title']}{visit_info}")
            lines.append(f"      {link['url']}")
            if link.get('tags'):
                lines.append(f"      Tags: {', '.join(link['tags'])}")
            lines.append("")
        
        return "\n".join(lines)


def get_tracker(subcommand=None, **kwargs):
    """CLI helper function."""
    tracker = LinkTracker()
    
    if subcommand == "add":
        url = kwargs.get("url")
        if not url:
            return {"error": "URL required. Usage: link add <url> [--title \"...\"] [--tags tag1,tag2]"}
        title = kwargs.get("title")
        tags = kwargs.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return tracker.add(url, title, tags)
    
    elif subcommand == "search":
        query = kwargs.get("query", "")
        results = tracker.search(query)
        if not results:
            return {"message": f"No links found matching '{query}'", "results": []}
        return {"results": results}
    
    elif subcommand == "visit":
        link_id = kwargs.get("link_id")
        if not link_id:
            return {"error": "Link ID required. Usage: link visit <id>"}
        return tracker.visit(link_id)
    
    elif subcommand == "delete":
        link_id = kwargs.get("link_id")
        if not link_id:
            return {"error": "Link ID required. Usage: link delete <id>"}
        return tracker.delete(link_id)
    
    elif subcommand == "top":
        limit = kwargs.get("limit", 10)
        return {"results": tracker.top(limit)}
    
    elif subcommand == "list":
        limit = kwargs.get("limit", 10)
        sort_by = kwargs.get("sort_by", "recent")
        return {"results": tracker.list(limit, sort_by)}
    
    elif subcommand == "stats":
        return tracker.stats()
    
    elif subcommand == "get":
        link_id = kwargs.get("link_id")
        if not link_id:
            return {"error": "Link ID required. Usage: link get <id>"}
        return tracker.get(link_id)
    
    else:
        # Default: list recent links
        return {"results": tracker.list(limit=10)}


if __name__ == "__main__":
    import sys
    
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    subcommand = args[0] if args else "list"
    
    kwargs = {}
    
    # Parse remaining args
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--title" and i + 1 < len(args):
            kwargs["title"] = args[i + 1]
            i += 2
        elif arg == "--tags" and i + 1 < len(args):
            kwargs["tags"] = args[i + 1].split(",")
            i += 2
        elif arg == "--limit" and i + 1 < len(args):
            kwargs["limit"] = int(args[i + 1])
            i += 2
        elif arg == "--sort" and i + 1 < len(args):
            kwargs["sort_by"] = args[i + 1]
            i += 2
        elif subcommand in ("add", "search", "visit", "delete", "get") and i == 1:
            # First arg after subcommand is the value
            if subcommand == "add":
                kwargs["url"] = arg
            elif subcommand in ("visit", "delete", "get"):
                kwargs["link_id"] = arg
            elif subcommand == "search":
                kwargs["query"] = arg
            i += 1
        else:
            i += 1
    
    result = get_tracker(subcommand, **kwargs)
    
    # Format output
    if isinstance(result, str):
        print(result)
    elif "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(json.dumps(result, indent=2))
