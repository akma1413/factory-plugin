# Obsidian Compound Skill — Knowledge Base Maintenance

## Trigger

User says "컴파운드", "지식 정리", "compound", "옵시디언 동기화", or invokes `/compound`.

## Purpose

Analyze all entries in the `kb/` knowledge base, identify relationships and patterns, and write compounded knowledge into an Obsidian vault with cross-linked references. This is a maintenance/housekeeping skill — it does NOT run during normal operation.

## Important

- The main harness works entirely without this skill — Obsidian is for long-term knowledge management only.
- Original entries in `kb/` are NEVER modified. Compound output goes to Obsidian only.
- This skill is run on-demand when the user explicitly requests it.

## Workflow

### Step 1: Inventory

Read all entries in `kb/`:
- `kb/cases/**/*.md` — all case entries
- `kb/principles/**/*.md` — all principle entries
- `kb/index.md` — current index

Build an internal map of all entries with their tags, types, and topics.

### Step 2: Analyze Relationships

Identify:

1. **Connections** — Cases that illustrate specific principles. Principles that explain why a case succeeded or failed.
2. **Clusters** — Groups of entries that address the same domain or problem space.
3. **Contradictions** — Entries that give conflicting advice. Flag these with both sides of the disagreement.
4. **Gaps** — Areas referenced by existing entries but not covered by any entry. Topics where only cases exist (missing principles) or only principles exist (missing real-world validation).
5. **Merge candidates** — Entries that overlap significantly and could be combined into a stronger, unified entry.

### Step 3: Structure for Obsidian

Organize the compounded knowledge into Obsidian-friendly markdown:

#### Entry Notes

For each `kb/` entry, create a corresponding Obsidian note that:
- Preserves the original content
- Adds `[[wikilinks]]` to related entries
- Adds a "Related" section at the bottom listing connections

#### Map of Content (MOC) Notes

Create topic-level MOC notes that:
- List all entries in that topic cluster
- Summarize the collective insight from the cluster
- Link to individual entry notes

#### Meta Notes

Create analysis notes:
- `_Contradictions.md` — list of conflicting entries with context
- `_Gaps.md` — identified knowledge gaps
- `_Merge Candidates.md` — entries that could be combined

### Step 4: Write to Obsidian

- If Obsidian MCP is available, use it to write notes to the vault
- If Obsidian MCP is NOT available, output the compounded structure as markdown files to a designated directory and inform the user

### Step 5: Report

Summarize the compound operation:

```
## Compound Report

### Stats
- Total entries processed: {n}
- Cases: {n} | Principles: {n}
- Connections found: {n}
- Clusters identified: {n}

### Findings
- Contradictions: {list or "none"}
- Gaps: {list or "none"}
- Merge candidates: {list or "none"}

### Output
- Notes written to: {location}
```

## Key Behaviors

- **Read-only on `kb/`.** Never modify the original knowledge base entries. All compound output goes to Obsidian.
- **Use `[[wikilinks]]` for cross-references.** This is Obsidian's native linking format. Link titles should match note titles exactly.
- **Tag propagation.** If a case is tagged `api-design` and a principle is tagged `api-design`, they should be linked in the Obsidian graph.
- **Be specific about contradictions.** Do not just say "these conflict." State what each entry claims and why they disagree.
- **Gaps are actionable.** Frame gaps as questions: "No principle covers error handling in background jobs — should we add one?"
- **Idempotent operation.** Running compound multiple times should produce the same result (overwrite previous compound output, not duplicate it).
