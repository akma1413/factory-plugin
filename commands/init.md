# /factory:init

Initialize a project with Factory agent harness structure.

Run this command in any project to set up the Factory agent harness. It creates the required directories, copies templates, and configures your project for use with Factory skills and hooks.

## What This Command Does

When you run `/factory:init`, the following will be created (skipping anything that already exists):

1. **Knowledge Base** — `kb/cases/`, `kb/principles/`, `kb/index.md`
   - Project-specific knowledge base for cases and principles
   - The Factory harness automatically scans this directory when providing context

2. **Spec Template** — `templates/spec.md`
   - Template for structured project specifications
   - Used by the `/factory:design` skill to capture your intent

3. **CLAUDE.md Harness Section** — Appended to project's `CLAUDE.md`
   - Adds Factory harness instructions to Claude's system context
   - Skipped if "Factory Agent Harness" section already exists
   - If `CLAUDE.md` doesn't exist, creates it

4. **Progress Tracking** — `PLAN.md` and `PROGRESS.md`
   - `PLAN.md`: Track what needs to be done
   - `PROGRESS.md`: Track where you left off
   - Skipped if files already exist

5. **Global Knowledge Base** — `~/.factory/kb/`
   - Shared knowledge base across all your projects
   - Entries here are available in every project using Factory

6. **Log Directory** — `logs/`
   - Used by the Factory recorder for decision logs
   - Added to `.gitignore` automatically

7. **Gitignore Update** — Adds `logs/` to `.gitignore`
   - Skipped if `logs/` is already in `.gitignore`
   - Creates `.gitignore` if it doesn't exist

## Idempotent

This command is safe to run multiple times. Existing files and directories are never overwritten. Only missing items are created.

## After Initialization

Your project is ready to use Factory skills:
- `/factory:design` — Extract and structure your intent
- `/factory:work-structure` — Decompose specs into agent teams
- `/factory:ingest` — Add knowledge from URLs to your KB
- `/factory:compound` — Sync KB to Obsidian

Check `PLAN.md` and `PROGRESS.md` to track your work.
