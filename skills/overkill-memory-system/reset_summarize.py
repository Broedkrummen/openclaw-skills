#!/usr/bin/env python3
"""
Reset & Summarize Module
Handles token optimization via session reset and summarization
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# Paths
MEMORY_BASE = Path.home() / ".openclaw" / "memory"
MEMORY_MD = MEMORY_BASE / "MEMORY.md"
DAILY_DIR = MEMORY_BASE / "daily"
RESET_HISTORY = MEMORY_BASE / "reset_history.json"

# Token threshold
TOKEN_THRESHOLD = 100000


def check_token_usage():
    """Check current session token usage"""
    # Try to get token info from session state
    session_state = MEMORY_BASE / "SESSION-STATE.md"
    session_json = MEMORY_BASE / "session.json"
    
    tokens = 0
    message_count = 0
    
    # Try JSON first (more accurate)
    if session_json.exists():
        try:
            with open(session_json) as f:
                data = json.load(f)
                tokens = data.get("total_tokens", 0)
                message_count = data.get("message_count", 0)
        except Exception:
            pass
    
    # Fallback: estimate from session state file
    if tokens == 0 and session_state.exists():
        content = session_state.read_text()
        # Rough estimate: ~10 tokens per word
        words = len(content.split())
        tokens = words * 10
        message_count = content.count("\n# ") + content.count("\n## ")
    
    return {
        "tokens": tokens,
        "message_count": message_count,
        "threshold": TOKEN_THRESHOLD,
        "percentage": round((tokens / TOKEN_THRESHOLD) * 100, 1) if tokens > 0 else 0
    }


def should_reset():
    """Check if session should be reset (>100k tokens)"""
    usage = check_token_usage()
    return usage["tokens"] >= TOKEN_THRESHOLD


def extract_facts_from_session():
    """Extract important facts from current session"""
    session_state = MEMORY_BASE / "SESSION-STATE.md"
    facts = []
    preferences = []
    projects = []
    
    if not session_state.exists():
        return {"facts": facts, "preferences": preferences, "projects": projects}
    
    content = session_state.read_text()
    
    # Extract facts (lines starting with - or * that look important)
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(("- ", "* ")) and len(line) > 10:
            # Check if it's a preference (contains prefer, like, dislike, etc.)
            if any(kw in line.lower() for kw in ["prefer", "like", "dislike", "hate", "want", "don't"]):
                preferences.append(line[2:])
            # Check if it's a project update
            elif any(kw in line.lower() for kw in ["project", "building", "working on", "creating", "implementing"]):
                projects.append(line[2:])
            else:
                facts.append(line[2:])
    
    return {
        "facts": facts[:50],  # Limit to 50
        "preferences": preferences[:20],
        "projects": projects[:20]
    }


def update_memory_md(facts_data):
    """Append extracted facts to MEMORY.md"""
    if not MEMORY_MD.exists():
        # Create with header
        MEMORY_MD.write_text("# MEMORY.md\n\n## Important Facts\n\n")
    
    current_content = MEMORY_MD.read_text()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Build update section
    updates = [f"\n## Session Reset - {timestamp}\n"]
    
    if facts_data["facts"]:
        updates.append("### Facts\n")
        for fact in facts_data["facts"][:10]:
            updates.append(f"- {fact}\n")
    
    if facts_data["preferences"]:
        updates.append("\n### Preferences\n")
        for pref in facts_data["preferences"][:5]:
            updates.append(f"- {pref}\n")
    
    if facts_data["projects"]:
        updates.append("\n### Projects\n")
        for proj in facts_data["projects"][:5]:
            updates.append(f"- {proj}\n")
    
    # Append to MEMORY.md
    MEMORY_MD.write_text(current_content + "\n".join(updates))
    return True


def update_daily_log(facts_data):
    """Update today's daily log with summary"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{today}.md"
    
    if not daily_file.exists():
        daily_file.parent.mkdir(parents=True, exist_ok=True)
        daily_file.write_text(f"# {today}\n\n")
    
    content = daily_file.read_text()
    timestamp = datetime.now().strftime("%H:%M")
    
    summary = [f"\n## Session Reset - {timestamp}\n"]
    summary.append(f"- Extracted {len(facts_data['facts'])} facts")
    summary.append(f"- Extracted {len(facts_data['preferences'])} preferences")
    summary.append(f"- Extracted {len(facts_data['projects'])} project updates\n")
    
    daily_file.write_text(content + "\n".join(summary))
    return True


def save_reset_history(facts_data, dry_run=False):
    """Save reset history to JSON"""
    history = []
    
    if RESET_HISTORY.exists():
        try:
            history = json.loads(RESET_HISTORY.read_text())
        except Exception:
            history = []
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tokens_before": check_token_usage()["tokens"],
        "facts_extracted": len(facts_data["facts"]),
        "preferences_extracted": len(facts_data["preferences"]),
        "projects_extracted": len(facts_data["projects"]),
        "dry_run": dry_run
    }
    
    history.append(entry)
    
    # Keep last 100 entries
    history = history[-100:]
    
    RESET_HISTORY.write_text(json.dumps(history, indent=2))
    return entry


def reset_and_summarize(dry_run=False):
    """
    Main reset & summarize function
    Extracts facts from session, updates MEMORY.md and daily log
    """
    print(f"Running reset_and_summarize (dry_run={dry_run})...")
    
    # Get current token usage
    usage = check_token_usage()
    print(f"Current token usage: {usage['tokens']:,} ({usage['percentage']}%)")
    
    # Extract facts
    facts_data = extract_facts_from_session()
    print(f"Extracted: {len(facts_data['facts'])} facts, "
          f"{len(facts_data['preferences'])} preferences, "
          f"{len(facts_data['projects'])} projects")
    
    if dry_run:
        print("\n[DRY RUN] Would save:")
        print(f"  - {len(facts_data['facts'])} facts to MEMORY.md")
        print(f"  - Summary to today's daily log")
        print(f"  - Entry to reset_history.json")
        
        # Save history but mark as dry_run
        save_reset_history(facts_data, dry_run=True)
        return {
            "action": "dry_run",
            "would_save": {
                "facts": len(facts_data["facts"]),
                "preferences": len(facts_data["preferences"]),
                "projects": len(facts_data["projects"])
            },
            "tokens": usage["tokens"]
        }
    
    # Actually perform the reset
    update_memory_md(facts_data)
    update_daily_log(facts_data)
    history_entry = save_reset_history(facts_data, dry_run=False)
    
    return {
        "action": "reset_complete",
        "saved": {
            "facts": len(facts_data["facts"]),
            "preferences": len(facts_data["preferences"]),
            "projects": len(facts_data["projects"])
        },
        "tokens": usage["tokens"],
        "history_entry": history_entry
    }


# CLI helpers
def cli_token_stats():
    """CLI: Show token usage stats"""
    usage = check_token_usage()
    status = "🔴 RESET NEEDED" if should_reset() else "🟢 OK"
    
    print(f"Session Token Usage:")
    print(f"  Tokens: {usage['tokens']:,} / {usage['threshold']:,} ({usage['percentage']}%)")
    print(f"  Messages: {usage['message_count']}")
    print(f"  Status: {status}")
    
    return usage


def cli_reset(dry_run=False):
    """CLI: Run reset and summarize"""
    if dry_run:
        print("=== DRY RUN MODE ===\n")
    
    result = reset_and_summarize(dry_run=dry_run)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            cli_token_stats()
        elif sys.argv[1] == "reset":
            dry = "--dry-run" in sys.argv
            cli_reset(dry_run=dry)
    else:
        print("Usage: reset_summarize.py [check|reset]")
