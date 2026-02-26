# Platform Post Tracking Integration

## Overview

Add ability to track posts made to social platforms (Discord, Telegram, etc.)

## What It Does

| Feature | Description |
|---------|-------------|
| Log post | Record when a post is made |
| Search posts | Find past posts by content/platform |
| Track links | Remember what was shared where |
| Timestamp | Know when something was posted |

## Storage

```
~/.openclaw/memory/
└── platform-posts.json
```

```json
{
  "posts": [
    {
      "id": "uuid",
      "platform": "discord",
      "channel": "general",
      "content": "Hello world",
      "link": "https://discord.com/...",
      "timestamp": "2026-02-25T12:00:00Z"
    }
  ]
}
```

## Implementation

### platform_posts.py

```python
class PlatformTracker:
    def __init__(self):
        self.file = Path("~/.openclaw/memory/platform-posts.json").expanduser()
        self.posts = json.loads(self.file.read_text()) if self.file.exists() else {"posts": []}
    
    def log_post(self, platform: str, channel: str, content: str, link: str = ""):
        post = {
            "id": str(uuid4()),
            "platform": platform,
            "channel": channel,
            "content": content,
            "link": link,
            "timestamp": datetime.now().isoformat()
        }
        self.posts["posts"].append(post)
        self._save()
        return post
    
    def search_posts(self, query: str) -> list:
        return [p for p in self.posts["posts"] if query.lower() in p["content"].lower()]
    
    def get_posts_by_platform(self, platform: str) -> list:
        return [p for p in self.posts["posts"] if p["platform"] == platform]
```

### CLI Commands

```bash
# Log a post
overkill platform log --platform discord --channel general --content "Hello" --link "https://..."

# Search posts
overkill platform search "query"

# List by platform
overkill platform list --platform discord

# Show recent posts
overkill platform recent --limit 10
```

---

*Platform post tracking integration*
