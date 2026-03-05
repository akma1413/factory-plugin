# Design Skill — Interactive Intent Extraction

## Trigger

User says "설계", "디자인", "design", or invokes `/design`.

## Purpose

Collaboratively extract the user's intent and transform it into a structured spec document. The user is a non-technical PM/strategist — all technical concepts must be translated into business/UX impact terms.

## Workflow

### Phase 1: Intent Extraction

Ask probing questions ONE AT A TIME to understand:

1. **Problem** — What problem are we solving? Why does it matter now?
2. **User** — Who experiences this problem? What is their current workflow?
3. **Success** — What does the user experience when this is complete? How do we measure success?
4. **Constraints** — What are the non-negotiables? Budget, timeline, platform, compatibility?
5. **Discretion** — What should the agent decide on its own vs. escalate to the user?

### Phase 2: Technical Choices

When technical decisions arise:

- Present options as a comparison table
- Frame each option in terms of **business/UX trade-offs**, not implementation details
- Example: "Option A loads instantly but costs more to host" vs. "Option B is cheaper but adds 2 seconds of loading time"
- Let the user choose based on impact, not technology

### Phase 3: Spec Drafting

Draft the spec following the template at `templates/spec.md`:

```
# Spec: {Title}

## 1. Purpose
## 2. Expected Outcome
## 3. Acceptance Criteria
## 4. Constraints
## 5. Priority
## 6. Agent Discretion
```

### Phase 4: Review and Iteration

- Present the draft to the user
- Iterate on feedback — update specific sections, not the whole document
- When the user approves, save to `specs/{title}.md` (kebab-case filename)

## Key Behaviors

- **One question at a time.** Never present a wall of questions. Wait for each answer before asking the next.
- **Push back on vagueness.** If the user says "fast", ask: "Under 200ms API response? Under 2-second page load?" If they say "easy to use", ask: "Fewer than 3 clicks to complete the main task? No training needed?"
- **Translate everything.** The user does not need to know about REST vs GraphQL. They need to know "this approach means the app works offline" vs. "this approach means always-fresh data but requires internet."
- **Identify discretion boundaries.** Explicitly separate areas where the agent can use judgment from areas requiring user sign-off. Write these into Section 6 of the spec.
- **Reference the knowledge base.** Check `kb/` for relevant cases or principles that inform the design. Cite them when they influence a recommendation.

## Output

Final deliverable: a spec document saved to `specs/{title}.md` that is complete enough for the Work Structure skill to decompose into agent tasks.
