#!/usr/bin/env python3
"""
Time-Based Search Module for overkill-memory-system
Search and filter memories by time ranges and natural language dates
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Memory paths
MEMORY_BASE = Path.home() / ".openclaw" / "memory"
DIARY_DIR = MEMORY_BASE / "diary"
DAILY_DIR = MEMORY_BASE / "daily"


class TimeSearch:
    """Time-based search for memory system"""
    
    def __init__(self, memory_path: Path = None):
        self.memory_path = memory_path or MEMORY_BASE
        self.diary_dir = DIARY_DIR
        self.daily_dir = DAILY_DIR
    
    def natural_time(self, query: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse natural time expressions like 'last week', 'yesterday', etc.
        
        Args:
            query: Natural language query containing time expression
            
        Returns:
            Tuple of (from_date, to_date) or None if no time expression found
        """
        now = datetime.now()
        query_lower = query.lower()
        
        # Time expression patterns
        patterns = {
            r"yesterday": (now - timedelta(days=1), now),
            r"last week": (now - timedelta(weeks=1), now),
            r"last month": (now - timedelta(days=30), now),
            r"last year": (now - timedelta(days=365), now),
            r"today": (now - timedelta(hours=24), now),
            r"past \s*(\d+)\s*days?": lambda m: (now - timedelta(days=int(m.group(1))), now),
            r"past \s*(\d+)\s*weeks?": lambda m: (now - timedelta(weeks=int(m.group(1))), now),
            r"past \s*(\d+)\s*months?": lambda m: (now - timedelta(days=30 * int(m.group(1))), now),
            r"past \s*(\d+)\s*hours?": lambda m: (now - timedelta(hours=int(m.group(1))), now),
            r"last \s*(\d+)\s*days?": lambda m: (now - timedelta(days=int(m.group(1))), now),
            r"(\d+)\s*days?\s*ago": lambda m: (now - timedelta(days=int(m.group(1))), now),
            r"(\d+)\s*hours?\s*ago": lambda m: (now - timedelta(hours=int(m.group(1))), now),
            r"(\d+)\s*weeks?\s*ago": lambda m: (now - timedelta(weeks=int(m.group(1))), now),
        }
        
        for pattern, result in patterns.items():
            if re.search(pattern, query_lower):
                if callable(result):
                    match = re.search(pattern, query_lower)
                    if match:
                        return result(match)
                return result
        
        return None
    
    def search_by_time(
        self, 
        query: str, 
        from_date: datetime = None, 
        to_date: datetime = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search memories within a time range.
        
        Args:
            query: Text query to search for
            from_date: Start date for search
            to_date: End date for search
            min_importance: Minimum importance score to include
            
        Returns:
            List of matching memories with metadata
        """
        results = []
        
        # Try natural time parsing if no explicit dates
        if from_date is None and to_date is None:
            parsed_time = self.natural_time(query)
            if parsed_time:
                from_date, to_date = parsed_time
        
        # Search diary entries
        results.extend(self._search_diary(query, from_date, to_date, min_importance))
        
        # Search daily files
        results.extend(self._search_daily(query, from_date, to_date, min_importance))
        
        # Search session state
        results.extend(self._search_session_state(query, from_date, to_date, min_importance))
        
        # Sort by date (most recent first)
        results.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return results
    
    def _search_diary(
        self, 
        query: str, 
        from_date: datetime, 
        to_date: datetime,
        min_importance: float
    ) -> List[Dict[str, Any]]:
        """Search diary entries"""
        results = []
        
        if not self.diary_dir.exists():
            return results
        
        query_lower = query.lower()
        
        for neuro_file in self.diary_dir.glob("*.neuro.json"):
            try:
                with open(neuro_file, 'r') as f:
                    data = json.load(f)
                
                file_date = self._parse_date_from_filename(neuro_file.name)
                
                # Filter by date range
                if from_date and file_date and file_date < from_date:
                    continue
                if to_date and file_date and file_date > to_date:
                    continue
                
                for memory in data.get("memories", []):
                    content = memory.get("content", "")
                    content_preview = memory.get("content_preview", "")
                    
                    if query_lower and query_lower not in content.lower() and query_lower not in content_preview.lower():
                        continue
                    
                    # Filter by importance
                    importance = memory.get("importance", 0.0)
                    if importance < min_importance:
                        continue
                    
                    results.append({
                        "source": "diary",
                        "file": str(neuro_file),
                        "date": memory.get("timestamp", ""),
                        "importance": importance,
                        "emotions": memory.get("emotions", []),
                        "content": content or content_preview,
                        "snippet": self._extract_snippet(content or content_preview, query)
                    })
                    
            except (json.JSONDecodeError, IOError) as e:
                continue
        
        return results
    
    def _search_daily(
        self, 
        query: str, 
        from_date: datetime, 
        to_date: datetime,
        min_importance: float
    ) -> List[Dict[str, Any]]:
        """Search daily memory files"""
        results = []
        
        if not self.daily_dir.exists():
            return results
        
        query_lower = query.lower()
        
        for daily_file in self.daily_dir.glob("*.md"):
            try:
                stat = daily_file.stat()
                file_mtime = datetime.fromtimestamp(stat.st_mtime)
                
                # Filter by date range using file modification time
                if from_date and file_mtime < from_date:
                    continue
                if to_date and file_mtime > to_date:
                    continue
                
                content = daily_file.read_text()
                
                if query_lower and query_lower not in content.lower():
                    continue
                
                results.append({
                    "source": "daily",
                    "file": str(daily_file),
                    "date": file_mtime.isoformat(),
                    "importance": 0.5,  # Default for daily files
                    "emotions": [],
                    "content": content,
                    "snippet": self._extract_snippet(content, query)
                })
                
            except IOError:
                continue
        
        return results
    
    def _search_session_state(
        self, 
        query: str, 
        from_date: datetime, 
        to_date: datetime,
        min_importance: float
    ) -> List[Dict[str, Any]]:
        """Search session state file"""
        results = []
        
        session_file = self.memory_path / "SESSION-STATE.md"
        if not session_file.exists():
            return results
        
        try:
            stat = session_file.stat()
            file_mtime = datetime.fromtimestamp(stat.st_mtime)
            
            # Filter by date range
            if from_date and file_mtime < from_date:
                return results
            if to_date and file_mtime > to_date:
                return results
            
            content = session_file.read_text()
            query_lower = query.lower()
            
            if query_lower and query_lower not in content.lower():
                return results
            
            results.append({
                "source": "session",
                "file": str(session_file),
                "date": file_mtime.isoformat(),
                "importance": 0.7,  # Session state is important
                "emotions": [],
                "content": content,
                "snippet": self._extract_snippet(content, query)
            })
            
        except IOError:
            pass
        
        return results
    
    def timeline(self, topic: str) -> List[Dict[str, Any]]:
        """
        Show chronological timeline of a topic across all memories.
        
        Args:
            topic: Topic to create timeline for
            
        Returns:
            List of memories containing the topic, sorted chronologically
        """
        results = []
        topic_lower = topic.lower()
        
        # Search diary
        for neuro_file in self.diary_dir.glob("*.neuro.json"):
            try:
                with open(neuro_file, 'r') as f:
                    data = json.load(f)
                
                file_date = self._parse_date_from_filename(neuro_file.name)
                
                for memory in data.get("memories", []):
                    content = (memory.get("content", "") + 
                              memory.get("content_preview", ""))
                    
                    if topic_lower in content.lower():
                        results.append({
                            "source": "diary",
                            "file": str(neuro_file),
                            "date": memory.get("timestamp", ""),
                            "importance": memory.get("importance", 0.0),
                            "content": content
                        })
                        
            except (json.JSONDecodeError, IOError):
                continue
        
        # Search daily files
        if self.daily_dir.exists():
            for daily_file in sorted(self.daily_dir.glob("*.md")):
                try:
                    content = daily_file.read_text()
                    
                    if topic_lower in content.lower():
                        results.append({
                            "source": "daily",
                            "file": str(daily_file),
                            "date": daily_file.name.replace(".md", ""),
                            "importance": 0.5,
                            "content": content[:500]  # Truncate for timeline
                        })
                        
                except IOError:
                    continue
        
        # Search MEMORY.md
        memory_md = self.memory_path / "MEMORY.md"
        if memory_md.exists():
            try:
                content = memory_md.read_text()
                
                if topic_lower in content.lower():
                    results.append({
                        "source": "curated",
                        "file": str(memory_md),
                        "date": "curated",
                        "importance": 0.8,
                        "content": content[:500]
                    })
                    
            except IOError:
                pass
        
        # Sort by date (oldest first for timeline)
        results.sort(key=lambda x: x.get("date", ""))
        
        return results
    
    def recent_memories(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent memories from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent memories
        """
        now = datetime.now()
        from_date = now - timedelta(days=days)
        
        return self.search_by_time("", from_date=from_date, to_date=now)
    
    def _parse_date_from_filename(self, filename: str) -> datetime:
        """Extract date from filename like 2026-02-25.neuro.json"""
        try:
            date_str = filename.split(".")[0]
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, IndexError):
            return None
    
    def _extract_snippet(self, content: str, query: str, context: int = 100) -> str:
        """Extract a snippet around the query match"""
        if not query:
            return content[:200]
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            return content[:200]
        
        start = max(0, pos - context)
        end = min(len(content), pos + len(query) + context)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet


# Standalone functions for CLI integration
def search_by_time(query: str, from_date: str = None, to_date: str = None, 
                   min_importance: float = 0.0) -> List[Dict[str, Any]]:
    """Convenience function for CLI"""
    ts = TimeSearch()
    
    from_dt = None
    to_dt = None
    
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
        except ValueError:
            from_dt = None
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            to_dt = None
    
    return ts.search_by_time(query, from_dt, to_dt, min_importance)


def get_timeline(topic: str) -> List[Dict[str, Any]]:
    """Convenience function for CLI"""
    ts = TimeSearch()
    return ts.timeline(topic)


def get_recent_memories(days: int = 7) -> List[Dict[str, Any]]:
    """Convenience function for CLI"""
    ts = TimeSearch()
    return ts.recent_memories(days)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: time_search.py <command> [args...]")
        print("Commands:")
        print("  search <query> [--from DATE] [--to DATE]")
        print("  timeline <topic>")
        print("  recent [--days N]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = search_by_time(query)
        print(json.dumps(results, indent=2))
        
    elif cmd == "timeline":
        topic = sys.argv[2] if len(sys.argv) > 2 else ""
        results = get_timeline(topic)
        print(json.dumps(results, indent=2))
        
    elif cmd == "recent":
        days = 7
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            if idx + 1 < len(sys.argv):
                days = int(sys.argv[idx + 1])
        results = get_recent_memories(days)
        print(json.dumps(results, indent=2))
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
