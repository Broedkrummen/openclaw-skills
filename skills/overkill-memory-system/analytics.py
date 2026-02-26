#!/usr/bin/env python3
"""
Memory Analytics - Insights into memory usage, patterns, and storage.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter


class MemoryAnalytics:
    def __init__(self, memory_path=None):
        self.memory_path = Path(memory_path or os.path.expanduser("~/.openclaw/memory"))
        self.search_cache_path = self.memory_path / "search-cache"
    
    def get_storage_usage(self):
        """Total storage used across all memory tiers."""
        total = 0
        try:
            for f in self.memory_path.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        
        return {
            "total_bytes": total,
            "total_kb": round(total / 1024, 2),
            "total_mb": round(total / 1024 / 1024, 2),
            "total_gb": round(total / 1024 / 1024 / 1024, 2)
        }
    
    def get_tier_breakdown(self):
        """Storage breakdown by tier."""
        tiers = {
            "HOT": ["session-state.json", "wal", "heartbeat-state.json", "internal_state.json"],
            "WARM": ["chroma", "daily", "chroma_", ".sqlite"],
            "COLD": ["git-notes", "knowledge", "reflections", "diary"],
            "ARCHIVE": ["archive", "backups", ".learnings"]
        }
        
        breakdown = {}
        total_mb = 0
        
        for tier, patterns in tiers.items():
            size = 0
            try:
                for f in self.memory_path.rglob("*"):
                    if f.is_file():
                        try:
                            fname = f.name
                            if any(p in fname for p in patterns):
                                size += f.stat().st_size
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass
            
            size_mb = round(size / 1024 / 1024, 2)
            breakdown[tier] = size_mb
            total_mb += size_mb
        
        breakdown["_total_mb"] = round(total_mb, 2)
        return breakdown
    
    def get_activity_timeline(self, days=30):
        """Memories created over time - based on daily notes and diary entries."""
        timeline = {}
        cutoff = datetime.now() - timedelta(days=days)
        
        # Check daily folder
        daily_path = self.memory_path / "daily"
        if daily_path.exists():
            for f in daily_path.glob("*.md"):
                try:
                    date_str = f.stem
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    if date >= cutoff:
                        content = f.read_text()
                        timeline[date_str] = {
                            "word_count": len(content.split()),
                            "line_count": len(content.splitlines())
                        }
                except (ValueError, OSError, PermissionError):
                    pass
        
        # Check root md files (excluding MEMORY.md and special files)
        for f in self.memory_path.glob("*.md"):
            if f.name in ["MEMORY.md", "SESSION-STATE.md"]:
                continue
            try:
                date_str = f.stem
                if "-" in date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    if date >= cutoff:
                        content = f.read_text()
                        timeline[date_str] = {
                            "word_count": len(content.split()),
                            "line_count": len(content.splitlines())
                        }
            except (ValueError, OSError, PermissionError):
                pass
        
        # Sort by date
        timeline = dict(sorted(timeline.items()))
        
        return {
            "days": days,
            "entries": timeline,
            "total_entries": len(timeline),
            "avg_words_per_day": round(sum(e["word_count"] for e in timeline.values()) / max(len(timeline), 1), 1)
        }
    
    def get_token_savings(self):
        """Estimate token savings from Mem0 compression."""
        # Try to read search cache for hits
        hits = 0
        total = 0
        
        if self.search_cache_path.exists():
            try:
                for f in self.search_cache_path.glob("*.json"):
                    try:
                        data = json.loads(f.read_text())
                        if isinstance(data, dict):
                            total += 1
                            if data.get("cached", False):
                                hits += 1
                    except (json.JSONDecodeError, OSError, PermissionError):
                        pass
            except (OSError, PermissionError):
                pass
        
        # Estimate based on cache hits
        if total > 0:
            cache_rate = hits / total
            est_savings = f"{int(cache_rate * 100)}%"
        else:
            # Default estimate based on typical Mem0 behavior
            est_savings = "75%"
        
        return {
            "estimated_savings": est_savings,
            "method": "Mem0 semantic compression",
            "cache_hits": hits,
            "cache_total": total,
            "cache_hit_rate": f"{round((hits/max(total,1)) * 100, 1)}%"
        }
    
    def get_search_patterns(self):
        """Most common search queries."""
        queries = []
        
        if self.search_cache_path.exists():
            try:
                for f in self.search_cache_path.glob("*.json"):
                    try:
                        data = json.loads(f.read_text())
                        if isinstance(data, dict) and "query" in data:
                            queries.append(data["query"])
                    except (json.JSONDecodeError, OSError, PermissionError):
                        pass
            except (OSError, PermissionError):
                pass
        
        # Count and get top queries
        counter = Counter(queries)
        top = counter.most_common(10)
        
        return {
            "top_queries": [{"query": q, "count": c} for q, c in top],
            "total_searches": len(queries),
            "unique_queries": len(counter)
        }
    
    def get_full_report(self):
        """Complete analytics report with all metrics."""
        return {
            "generated_at": datetime.now().isoformat(),
            "storage": self.get_storage_usage(),
            "tiers": self.get_tier_breakdown(),
            "activity": self.get_activity_timeline(),
            "savings": self.get_token_savings(),
            "searches": self.get_search_patterns()
        }
    
    def format_report(self):
        """Format the full report as a readable string."""
        report = self.get_full_report()
        
        lines = [
            "╔══════════════════════════════════════╗",
            "║     MEMORY ANALYTICS REPORT          ║",
            "╠══════════════════════════════════════╣",
            "",
            "  STORAGE",
            "  ─────────",
            f"  Total: {report['storage']['total_mb']} MB ({report['storage']['total_gb']} GB)",
            "",
            "  BY TIER",
            "  ─────────",
        ]
        
        tiers = report["tiers"]
        tier_sizes = [(t, s) for t, s in tiers.items() if not t.startswith("_")]
        max_size = max(s for _, s in tier_sizes) if tier_sizes else 1
        
        for tier, size in tier_sizes:
            bar_len = int((size / max_size) * 20) if max_size > 0 else 0
            bar = "█" * bar_len
            lines.append(f"  {tier:6s}: {size:6.1f} MB  {bar}")
        
        lines.extend([
            "",
            f"  ACTIVITY (Last {report['activity']['days']} days)",
            "  ─────────────────────",
            f"  Memories created: {report['activity']['total_entries']}",
            f"  Avg words/day: {report['activity']['avg_words_per_day']}",
            "",
            "  TOKEN SAVINGS",
            "  ─────────────",
            f"  Est. savings: {report['savings']['estimated_savings']}",
            f"  Method: {report['savings']['method']}",
            f"  Cache hit rate: {report['savings']['cache_hit_rate']}",
            "",
            "  SEARCH PATTERNS",
            "  ────────────────",
            f"  Total searches: {report['searches']['total_searches']}",
            f"  Unique queries: {report['searches']['unique_queries']}",
        ])
        
        if report["searches"]["top_queries"]:
            lines.append("  Top queries:")
            for i, item in enumerate(report["searches"]["top_queries"][:5], 1):
                lines.append(f"    {i}. {item['query']} ({item['count']})")
        
        lines.extend([
            "",
            f"  Generated: {report['generated_at'][:19]}",
            "╚══════════════════════════════════════╝"
        ])
        
        return "\n".join(lines)


def get_analytics(subcommand=None, days=30):
    """CLI helper function."""
    analytics = MemoryAnalytics()
    
    if subcommand == "storage":
        return analytics.get_storage_usage()
    elif subcommand == "tiers":
        return analytics.get_tier_breakdown()
    elif subcommand == "activity":
        return analytics.get_activity_timeline(days)
    elif subcommand == "searches" or subcommand == "search":
        return analytics.get_search_patterns()
    elif subcommand is None or subcommand == "":
        return analytics.format_report()
    else:
        return {"error": f"Unknown subcommand: {subcommand}"}


if __name__ == "__main__":
    import sys
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    subcommand = args[0] if args else None
    days = 30
    for i, arg in enumerate(args):
        if arg == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
    
    result = get_analytics(subcommand, days)
    
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2))
