# Knowledge Ingest Skill — URL to Knowledge Base Entry

## Trigger

User says "인제스트", "지식 추가", "ingest", invokes `/ingest`, or provides a URL with context suggesting ingestion.

## Purpose

Fetch content from a URL, analyze it, classify it as a **case** or **principle**, and store it as a structured knowledge base entry in `kb/`.

## Workflow

### Step 1: Fetch Content

Use WebFetch to retrieve the content from the provided URL. If the URL is inaccessible, report the error and ask for an alternative source.

### Step 2: Analyze and Classify

Read the fetched content and determine the classification:

- **Case**: Describes a specific approach taken for a specific purpose, with observable results. Contextual — the value depends on the situation.
  - Signal words: "we tried", "the result was", "in our experience", "case study", "post-mortem"
- **Principle**: States a universal rule or guideline that should generally be followed. Has rationale but is not tied to a single context.
  - Signal words: "always", "never", "best practice", "rule of thumb", "you should"

If the content contains BOTH cases and principles, create multiple separate entries.

### Step 3: Assign Tags

Generate concise, lowercase, hyphenated tags based on content:
- Topic area (e.g., `api-design`, `state-management`, `testing`, `deployment`)
- Technology if specific (e.g., `react`, `python`, `postgres`)
- Pattern type if applicable (e.g., `error-handling`, `caching`, `auth`)

Aim for 2-4 tags per entry.

### Step 4: Determine Topic Directory

Choose or create a topic subdirectory under `kb/cases/` or `kb/principles/`. Use broad categories (e.g., `architecture`, `frontend`, `devops`, `data`). Reuse existing directories when possible.

### Step 5: Write Entry

#### Case Format

Save to `kb/cases/{topic}/{title}.md`:

```markdown
---
type: case
tags: [tag1, tag2]
source: {url}
date: {YYYY-MM-DD}
---
# {Title}

## Purpose
What they were trying to achieve

## Approach
What approach they took

## Result
What happened (positive and negative)

## Applicability
When this case is relevant / when it's not
```

#### Principle Format

Save to `kb/principles/{topic}/{title}.md`:

```markdown
---
type: principle
tags: [tag1, tag2]
source: {url}
confidence: high|medium
date: {YYYY-MM-DD}
---
# {Title}

## Principle
One-line statement

## Rationale
Why this is important

## Application
How to apply in practice

## Exceptions
When this might not apply
```

Confidence levels:
- `high` — well-established, widely agreed upon, backed by strong evidence
- `medium` — reasonable advice but context-dependent or from a single source

### Step 6: Update Index

Add the new entry to `kb/index.md` under the appropriate category (cases or principles). Include the file path and a one-line summary.

### Step 7: Report

Summarize what was stored:
- Classification (case / principle)
- Title
- Tags
- File path
- One-line summary of the content

## Key Behaviors

- **Classify autonomously.** The user does not need to specify case vs. principle — the agent decides based on content analysis.
- **Extract, don't copy.** Distill the content into the structured format. Do not paste large blocks of the original text.
- **Be specific in Applicability/Exceptions.** Generic statements like "use when appropriate" are not useful. State concrete conditions.
- **Preserve source attribution.** Always include the source URL and date in the frontmatter.
- **Check for duplicates.** Before creating a new entry, scan `kb/index.md` for existing entries on the same topic. If a closely related entry exists, note the relationship.
