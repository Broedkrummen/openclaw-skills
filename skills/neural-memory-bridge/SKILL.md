---
name: neural-memory-bridge
description: Bridge skill to call NeuralMemory (nmem) from OpenClaw via the exec tool. Use to remember and recall associative memories without native MCP support.
homepage: https://github.com/nhadaututtheky/neural-memory
metadata: {"clawdbot":{"emoji":"🧠","requires":{"bins":["/home/broedkrummen/.neuralmemory-venv/bin/nmem"]}}}
---

# NeuralMemory Bridge Skill

This skill lets Nova call **NeuralMemory** via the `exec` tool, without needing OpenClaw's built-in MCP support.

NeuralMemory is installed in a dedicated venv:

- Venv: `/home/broedkrummen/.neuralmemory-venv`
- CLI: `/home/broedkrummen/.neuralmemory-venv/bin/nmem`
- Brain: `default`

We use two core commands:

- `nmem remember` — store a memory
- `nmem recall`   — recall memories by associative graph search

## Usage Patterns

### 1. Remember a memory

Use after an important decision, insight, or preference that should live in NeuralMemory as well as file/Voyage memory.

```bash
/home/broedkrummen/.neuralmemory-venv/bin/nmem remember \
  --content "<TEXT>" \
  --type decision \
  --tags "openclaw,config" \
  --priority 8
```

From Nova (via exec):

- When Kasper says **"remember this long term"** and we specifically want it in NeuralMemory too, call `exec` with the command above, filling in:
  - `--content` = the text to store
  - `--type`    = `fact | decision | preference | todo | insight | error | context | workflow | reference`
  - `--tags`    = comma-separated tags
  - `--priority`= 0–10 (default 5; use 7–10 for important stuff)

### 2. Recall memories

Use when Kasper asks things like:

- "Do you remember why X happened?"
- "What did we decide about Y?"
- "What do we know about Z?"

```bash
/home/broedkrummen/.neuralmemory-venv/bin/nmem recall \
  --query "<QUESTION OR TOPIC>" \
  --depth 1 \
  --max 5 \
  --json
```

From Nova (via exec):

- Prefer `depth 1` for normal recall; use `depth 2` when tracing causes ("why did X happen?").
- Always pass `--json` so output is machine-readable and can be summarized.

### 3. Health / debug (manual)

Kasper can run these directly in a shell when needed:

```bash
/home/broedkrummen/.neuralmemory-venv/bin/nmem stats
/home/broedkrummen/.neuralmemory-venv/bin/nmem health
```

Nova should not run destructive commands (e.g. brain reset) without explicit instruction.

## Integration Rules

- **No more `openclaw.json` edits for MCP** on this version. This bridge uses `exec` only.
- Use NeuralMemory as a **secondary** memory system alongside:
  - Tiered file memory (MEMORY.md + memory/domains + logs)
  - Voyage + memory-system-v2
- Store only high-value, durable memories here, not every message.
- When in doubt, prefer the existing Voyage/file stack; NeuralMemory is for extra associative recall, not the primary store.
