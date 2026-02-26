#!/usr/bin/env python3
"""
Dissolve/cleanup sub-agent workspaces.

Usage:
    python3 scripts/dissolve_agents.py --workspace <path> --archive
    python3 scripts/dissolve_agents.py --workspace <path> --delete
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime


def dissolve_agents(workspace: str, archive: bool = False, delete: bool = False) -> None:
    """Cleanup agent workspaces."""
    
    workspace_path = Path(workspace)
    
    if not workspace_path.exists():
        print(f"Error: Workspace not found: {workspace}")
        sys.exit(1)
    
    if not archive and not delete:
        print("Error: Must specify either --archive or --delete")
        sys.exit(1)
    
    # Find all agent directories (those with status.json)
    agent_dirs = []
    for item in workspace_path.iterdir():
        if item.is_dir() and (item / "status.json").exists():
            agent_dirs.append(item)
    
    if not agent_dirs:
        print("No agent workspaces found to dissolve.")
        return
    
    print(f"Found {len(agent_dirs)} agent workspace(s)")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = workspace_path / f"archive_{timestamp}"
    
    if archive:
        archive_path.mkdir(parents=True, exist_ok=True)
        print(f"Archiving to: {archive_path}")
    
    for agent_dir in agent_dirs:
        agent_name = agent_dir.name
        
        # Read final status
        status_file = agent_dir / "status.json"
        if status_file.exists():
            status = json.loads(status_file.read_text())
            print(f"\n{agent_name}: {status.get('state', 'unknown')}")
        
        if archive:
            dest = archive_path / agent_name
            shutil.move(str(agent_dir), str(dest))
            print(f"  → Archived: {dest}")
        elif delete:
            shutil.rmtree(agent_dir)
            print(f"  → Deleted: {agent_dir}")
    
    print("\n✓ Dissolve complete")
    
    if archive:
        print(f"Archive location: {archive_path}")


def main():
    parser = argparse.ArgumentParser(description="Dissolve sub-agent workspaces")
    parser.add_argument("--workspace", "-w", required=True, help="Workspace path containing agents")
    parser.add_argument("--archive", action="store_true", help="Archive agents instead of deleting")
    parser.add_argument("--delete", action="store_true", help="Delete agents permanently")
    
    args = parser.parse_args()
    
    dissolve_agents(args.workspace, args.archive, args.delete)


if __name__ == "__main__":
    main()
