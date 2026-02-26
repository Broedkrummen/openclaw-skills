#!/usr/bin/env python3
"""
Create a sub-agent workspace for the agent-orchestrator skill.

Usage:
    python3 scripts/create_agent.py <agent-name> --workspace <path>
"""

import argparse
import json
import os
import sys
from pathlib import Path


def create_agent(agent_name: str, workspace: str = None) -> str:
    """Create a sub-agent workspace with inbox, outbox, and workspace directories."""
    
    if workspace is None:
        workspace = os.getcwd()
    
    agent_path = Path(workspace) / agent_name
    
    if agent_path.exists():
        print(f"Error: Agent directory already exists: {agent_path}")
        sys.exit(1)
    
    # Create directories
    (agent_path / "inbox").mkdir(parents=True)
    (agent_path / "outbox").mkdir(parents=True)
    (agent_path / "workspace").mkdir(parents=True)
    
    # Create default SKILL.md
    skill_md = f"""# {agent_name}

Generated sub-agent for agent-orchestrator.

## Role
[Describe this agent's role and objective]

## Tools
[Define available tools and capabilities]

## Input
- Read task from `inbox/instructions.md`
- Read input files from `inbox/`

## Output
- Write completed work to `outbox/`
- Update `status.json` when complete

## Success Criteria
[Define success criteria for this agent]
"""
    
    (agent_path / "SKILL.md").write_text(skill_md)
    
    # Create default instructions template
    (agent_path / "inbox" / "instructions.md").write_text("""# Task Instructions

## Objective
[What this agent should accomplish]

## Deliverables
- [Deliverable 1]
- [Deliverable 2]

## Success Criteria
[What constitutes successful completion]

## Notes
[Any additional context or requirements]
""")
    
    # Create status.json
    status = {
        "state": "pending",
        "started": None,
        "completed": None,
        "agent": agent_name,
        "workspace": str(agent_path)
    }
    (agent_path / "status.json").write_text(json.dumps(status, indent=2))
    
    print(f"✓ Created agent: {agent_name}")
    print(f"  Path: {agent_path}")
    print(f"  Structure:")
    print(f"    ├── SKILL.md")
    print(f"    ├── inbox/")
    print(f"    │   └── instructions.md")
    print(f"    ├── outbox/")
    print(f"    ├── workspace/")
    print(f"    └── status.json")
    
    return str(agent_path)


def main():
    parser = argparse.ArgumentParser(description="Create a sub-agent workspace")
    parser.add_argument("agent_name", help="Name of the agent to create")
    parser.add_argument("--workspace", "-w", help="Parent workspace path (default: cwd)")
    
    args = parser.parse_args()
    
    create_agent(args.agent_name, args.workspace)


if __name__ == "__main__":
    main()
