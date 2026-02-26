#!/usr/bin/env python3
"""
Platform Post Tracking Module
Tracks posts made to social platforms (Discord, Telegram, etc.)
"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Storage path
PLATFORM_POSTS_FILE = Path.home() / ".openclaw" / "memory" / "platform-posts.json"


class PlatformTracker:
    """Track posts made to social platforms"""
    
    def __init__(self, storage_path: str = None):
        self.file = Path(storage_path) if storage_path else PLATFORM_POSTS_FILE
        self.posts = self._load()
    
    def _load(self) -> dict:
        """Load posts from storage file"""
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except json.JSONDecodeError:
                return {"posts": []}
        return {"posts": []}
    
    def _save(self):
        """Save posts to storage file"""
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.posts, indent=2))
    
    def log_post(self, platform: str, channel: str, content: str, link: str = "") -> dict:
        """
        Log a new post to a platform.
        
        Args:
            platform: Platform name (e.g., discord, telegram, twitter)
            channel: Channel or destination name
            content: Post content
            link: Optional link to the post
        
        Returns:
            The created post dict
        """
        post = {
            "id": str(uuid4()),
            "platform": platform.lower(),
            "channel": channel,
            "content": content,
            "link": link,
            "timestamp": datetime.now().isoformat()
        }
        self.posts["posts"].append(post)
        self._save()
        return post
    
    def search_posts(self, query: str) -> list:
        """
        Search posts by query string.
        
        Args:
            query: Search query to match against content
        
        Returns:
            List of matching posts
        """
        query_lower = query.lower()
        return [
            p for p in self.posts["posts"]
            if query_lower in p["content"].lower() or 
               query_lower in p["platform"].lower() or
               query_lower in p["channel"].lower()
        ]
    
    def get_posts_by_platform(self, platform: str) -> list:
        """
        Get all posts for a specific platform.
        
        Args:
            platform: Platform name to filter by
        
        Returns:
            List of posts from that platform
        """
        platform_lower = platform.lower()
        return [p for p in self.posts["posts"] if p["platform"] == platform_lower]
    
    def get_recent_posts(self, limit: int = 10) -> list:
        """
        Get the most recent posts.
        
        Args:
            limit: Maximum number of posts to return
        
        Returns:
            List of recent posts (most recent first)
        """
        sorted_posts = sorted(
            self.posts["posts"],
            key=lambda p: p.get("timestamp", ""),
            reverse=True
        )
        return sorted_posts[:limit]
    
    def list_all(self) -> list:
        """Get all posts"""
        return self.posts["posts"]


# CLI helper functions
def cli_log_post(platform: str, channel: str, content: str, link: str = "") -> dict:
    """CLI wrapper for log_post"""
    tracker = PlatformTracker()
    return tracker.log_post(platform, channel, content, link)


def cli_search_posts(query: str) -> list:
    """CLI wrapper for search_posts"""
    tracker = PlatformTracker()
    return tracker.search_posts(query)


def cli_list_platform(platform: str = None) -> list:
    """CLI wrapper for get_posts_by_platform"""
    tracker = PlatformTracker()
    if platform:
        return tracker.get_posts_by_platform(platform)
    return tracker.list_all()


def cli_recent_posts(limit: int = 10) -> list:
    """CLI wrapper for get_recent_posts"""
    tracker = PlatformTracker()
    return tracker.get_recent_posts(limit)


if __name__ == "__main__":
    # Test/simple demo
    tracker = PlatformTracker()
    print(f"Platform tracker initialized. Storage: {tracker.file}")
    print(f"Total posts: {len(tracker.posts['posts'])}")
