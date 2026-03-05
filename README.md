# Factory Plugin for Claude Code

Agent harness that manages coding agents like an OS manages processes. Structured workflow: **intake → planning → execution → verification → delivery**.

## Installation

```bash
claude /install-plugin https://github.com/akma1413/factory-plugin
```

## What's Included

### 4 Skills

| Skill | Description |
|-------|-------------|
| `/factory:design` | Extract user intent through structured questioning |
| `/factory:work-structure` | Decompose specs into sub-agent teams |
| `/factory:ingest` | Add knowledge from URLs to your KB |
| `/factory:compound` | Sync KB to Obsidian |

### 2 Hooks

- **Stop** → `verify_completion`: Intercepts "done" signals and forces quality checks
- **PreToolUse** → `mediate_tools`: Watches for agents going in circles

### 1 Command

- `/factory:init` — Initialize a new project with Factory harness structure

## Quick Start

1. **Initialize a project**:
   ```
   /factory:init
   ```
   This creates: `kb/`, `templates/spec.md`, `CLAUDE.md` harness section, `PLAN.md`, `PROGRESS.md`

2. **Design your spec**:
   ```
   /factory:design
   ```
   Answer structured questions to capture your intent

3. **Work-structure decomposes it**:
   ```
   /factory:work-structure
   ```
   Breaks spec into parallel agent teams

4. **Automatic verification** triggers on "done" via Stop hook

## Project Structure (after /factory:init)

```
your-project/
├── kb/
│   ├── cases/          # Case studies and examples
│   ├── principles/     # Reusable principles
│   └── index.md        # KB index
├── templates/
│   └── spec.md         # Spec template
├── PLAN.md             # What needs to be done
├── PROGRESS.md         # Where we left off
└── CLAUDE.md           # Factory harness instructions (auto-added)
```

## Dual Knowledge Base

Factory scans **two** KB locations:
1. **Project KB**: `./kb/` (project-specific knowledge)
2. **Global KB**: `~/.factory/kb/` (shared across all projects)

Project entries take priority when there are duplicates.

## Requirements

- Python >= 3.11 (for bundled harness modules)
- Claude Code with plugin support

## License

MIT

## Author

[@akma1413](https://github.com/akma1413)
