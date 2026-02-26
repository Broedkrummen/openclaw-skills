#!/usr/bin/env python3
"""
Importance Ranking Module for overkill-memory-system
Rank memories by importance based on frequency, corrections, emotions, and recency
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Memory paths
MEMORY_BASE = Path.home() / ".openclaw" / "memory"
DIARY_DIR = MEMORY_BASE / "diary"
DAILY_DIR = MEMORY_BASE / "daily"


class ImportanceRanker:
    """Rank memories by importance using weighted scoring"""
    
    # Default weights for importance calculation
    DEFAULT_WEIGHTS = {
        "frequency": 0.3,    # How often topic is mentioned
        "correction": 0.25,  # User corrections/adjustments
        "emotional": 0.25,   # Emotional weight
        "recency": 0.2       # How recent
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize the importance ranker.
        
        Args:
            weights: Custom weights (uses defaults if not provided)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def calculate_importance(self, memory: Dict[str, Any]) -> float:
        """
        Calculate importance score for a single memory.
        
        Args:
            memory: Memory dictionary with content, metadata
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        score = 0.0
        content = memory.get("content", "") or memory.get("content_preview", "")
        
        # Frequency score (0-0.3)
        freq_score = self._calculate_frequency_score(content)
        score += freq_score * self.weights["frequency"]
        
        # Correction score (0-0.25)
        correction_score = self._calculate_correction_score(memory)
        score += correction_score * self.weights["correction"]
        
        # Emotional score (0-0.25)
        emotional_score = self._calculate_emotional_score(memory)
        score += emotional_score * self.weights["emotional"]
        
        # Recency score (0-0.2)
        recency_score = self._calculate_recency_score(memory)
        score += recency_score * self.weights["recency"]
        
        # Normalize to 0-1
        return min(score, 1.0)
    
    def _calculate_frequency_score(self, content: str) -> float:
        """
        Calculate frequency score based on content richness.
        More content = more mentions = higher frequency score.
        """
        if not content:
            return 0.0
        
        # Normalize by typical content length
        content_length = len(content)
        return min(content_length / 2000, 1.0)  # 2000 chars = max score
    
    def _calculate_correction_score(self, memory: Dict[str, Any]) -> float:
        """Calculate score based on correction/feedback indicators"""
        # Check for correction flags
        if memory.get("was_corrected", False):
            return 1.0
        
        if memory.get("correction_count", 0) > 0:
            return min(memory.get("correction_count", 0) / 5, 1.0)
        
        # Check content for correction indicators
        content = (memory.get("content", "") + 
                  memory.get("content_preview", "")).lower()
        
        correction_indicators = [
            "actually", "wait", "no,", "correction", 
            "updated", "changed", "fixed", "oops"
        ]
        
        indicator_count = sum(1 for ind in correction_indicators if ind in content)
        return min(indicator_count / 3, 1.0)
    
    def _calculate_emotional_score(self, memory: Dict[str, Any]) -> float:
        """Calculate score based on emotional content"""
        emotions = memory.get("emotions", [])
        
        if not emotions:
            # Try to detect emotions from content
            content = (memory.get("content", "") + 
                      memory.get("content_preview", "")).lower()
            
            emotion_indicators = {
                "joy": ["happy", "joy", "excited", "great", "wonderful"],
                "anger": ["angry", "frustrated", "annoyed", "hate"],
                "sadness": ["sad", "depressed", "down", "unhappy"],
                "fear": ["scared", "afraid", "worried", "anxious"],
                "surprise": ["surprised", "amazing", "unexpected", "wow"],
                "anticipation": ["looking forward", "hope", "expect"]
            }
            
            detected = set()
            for emotion, indicators in emotion_indicators.items():
                if any(ind in content for ind in indicators):
                    detected.add(emotion)
            
            emotions = list(detected)
        
        # Score based on number and intensity of emotions
        if not emotions:
            return 0.0
        
        # More emotions = higher score (up to 5)
        return min(len(emotions) / 5, 1.0)
    
    def _calculate_recency_score(self, memory: Dict[str, Any]) -> float:
        """Calculate score based on how recent the memory is"""
        # Try to get timestamp from memory
        timestamp_str = memory.get("timestamp") or memory.get("date", "")
        
        if not timestamp_str or timestamp_str == "curated":
            return 0.5  # Default for undated content
        
        try:
            # Try parsing ISO format
            if isinstance(timestamp_str, str):
                if "T" in timestamp_str:
                    memory_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    memory_date = datetime.strptime(timestamp_str, "%Y-%m-%d")
            else:
                memory_date = timestamp_str
        except (ValueError, TypeError):
            return 0.5  # Default for unparseable dates
        
        # Calculate age in days
        age_days = (datetime.now() - memory_date).days
        
        # Exponential decay: recent = high score
        if age_days < 0:
            age_days = 0  # Future dates treated as now
        
        # Half-life of 30 days: 30 days ago = 0.5, 90 days ago = ~0.125
        import math
        recency = math.exp(-age_days / 30)
        
        return recency
    
    def rank_by_importance(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank a list of memories by importance.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            List sorted by importance (highest first), with importance scores added
        """
        # Calculate importance for each memory
        for memory in memories:
            memory["importance"] = self.calculate_importance(memory)
        
        # Sort by importance descending
        return sorted(memories, key=lambda x: x.get("importance", 0.0), reverse=True)
    
    def top_memories(self, limit: int = 10, min_importance: float = 0.0) -> List[Dict[str, Any]]:
        """
        Get the most important memories.
        
        Args:
            limit: Maximum number of memories to return
            min_importance: Minimum importance threshold
            
        Returns:
            List of top memories
        """
        all_memories = self._load_all_memories()
        ranked = self.rank_by_importance(all_memories)
        
        # Filter by minimum importance
        if min_importance > 0:
            ranked = [m for m in ranked if m.get("importance", 0.0) >= min_importance]
        
        return ranked[:limit]
    
    def _load_all_memories(self) -> List[Dict[str, Any]]:
        """Load all memories from various sources"""
        memories = []
        
        # Load from diary
        memories.extend(self._load_diary_memories())
        
        # Load from daily files
        memories.extend(self._load_daily_memories())
        
        # Load from session state
        memories.extend(self._load_session_memories())
        
        # Load from curated memory
        memories.extend(self._load_curated_memories())
        
        return memories
    
    def _load_diary_memories(self) -> List[Dict[str, Any]]:
        """Load memories from diary"""
        memories = []
        
        if not DIARY_DIR.exists():
            return memories
        
        for neuro_file in DIARY_DIR.glob("*.neuro.json"):
            try:
                with open(neuro_file, 'r') as f:
                    data = json.load(f)
                
                memories.extend(data.get("memories", []))
                
            except (json.JSONDecodeError, IOError):
                continue
        
        return memories
    
    def _load_daily_memories(self) -> List[Dict[str, Any]]:
        """Load memories from daily files"""
        memories = []
        
        if not DAILY_DIR.exists():
            return memories
        
        for daily_file in DAILY_DIR.glob("*.md"):
            try:
                content = daily_file.read_text()
                stat = daily_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                memories.append({
                    "source": "daily",
                    "content": content,
                    "date": mtime.isoformat(),
                    "importance": 0.5,
                    "emotions": []
                })
                
            except IOError:
                continue
        
        return memories
    
    def _load_session_memories(self) -> List[Dict[str, Any]]:
        """Load from session state"""
        memories = []
        
        session_file = MEMORY_BASE / "SESSION-STATE.md"
        if session_file.exists():
            try:
                content = session_file.read_text()
                stat = session_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                memories.append({
                    "source": "session",
                    "content": content,
                    "date": mtime.isoformat(),
                    "importance": 0.7,
                    "emotions": []
                })
                
            except IOError:
                pass
        
        return memories
    
    def _load_curated_memories(self) -> List[Dict[str, Any]]:
        """Load from curated MEMORY.md"""
        memories = []
        
        memory_md = MEMORY_BASE / "MEMORY.md"
        if memory_md.exists():
            try:
                content = memory_md.read_text()
                
                memories.append({
                    "source": "curated",
                    "content": content,
                    "date": "curated",
                    "importance": 0.8,
                    "emotions": []
                })
                
            except IOError:
                pass
        
        return memories
    
    def importance_stats(self) -> Dict[str, Any]:
        """
        Get statistics about importance distribution.
        
        Returns:
            Dictionary with importance statistics
        """
        all_memories = self._load_all_memories()
        
        if not all_memories:
            return {
                "total_memories": 0,
                "avg_importance": 0.0,
                "high_importance_count": 0,
                "medium_importance_count": 0,
                "low_importance_count": 0,
                "by_source": {}
            }
        
        # Calculate importance for all
        for mem in all_memories:
            mem["calculated_importance"] = self.calculate_importance(mem)
        
        importances = [m.get("calculated_importance", 0.0) for m in all_memories]
        
        # Categorize
        high = sum(1 for i in importances if i >= 0.7)
        medium = sum(1 for i in importances if 0.3 <= i < 0.7)
        low = sum(1 for i in importances if i < 0.3)
        
        # By source
        by_source = {}
        for mem in all_memories:
            source = mem.get("source", "unknown")
            if source not in by_source:
                by_source[source] = {"count": 0, "total_importance": 0.0}
            by_source[source]["count"] += 1
            by_source[source]["total_importance"] += mem.get("calculated_importance", 0.0)
        
        # Calculate averages
        for source in by_source:
            count = by_source[source]["count"]
            if count > 0:
                by_source[source]["avg_importance"] = by_source[source]["total_importance"] / count
        
        return {
            "total_memories": len(all_memories),
            "avg_importance": sum(importances) / len(importances) if importances else 0.0,
            "high_importance_count": high,
            "medium_importance_count": medium,
            "low_importance_count": low,
            "by_source": by_source,
            "weights_used": self.weights
        }


# Standalone functions for CLI integration
def calculate_importance(memory: Dict[str, Any]) -> float:
    """Convenience function for CLI"""
    ranker = ImportanceRanker()
    return ranker.calculate_importance(memory)


def rank_memories(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function for CLI"""
    ranker = ImportanceRanker()
    return ranker.rank_by_importance(memories)


def get_top_memories(limit: int = 10, min_importance: float = 0.0) -> List[Dict[str, Any]]:
    """Convenience function for CLI"""
    ranker = ImportanceRanker()
    return ranker.top_memories(limit, min_importance)


def get_importance_stats() -> Dict[str, Any]:
    """Convenience function for CLI"""
    ranker = ImportanceRanker()
    return ranker.importance_stats()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: importance_ranker.py <command> [args...]")
        print("Commands:")
        print("  top [--limit N] [--min-importance N]")
        print("  stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "top":
        limit = 10
        min_imp = 0.0
        
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        
        if "--min-importance" in sys.argv:
            idx = sys.argv.index("--min-importance")
            if idx + 1 < len(sys.argv):
                min_imp = float(sys.argv[idx + 1])
        
        results = get_top_memories(limit, min_imp)
        print(json.dumps(results, indent=2, default=str))
        
    elif cmd == "stats":
        stats = get_importance_stats()
        print(json.dumps(stats, indent=2, default=str))
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
