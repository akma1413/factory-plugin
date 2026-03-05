# Work Structure Skill — Spec to Sub-Agent Team

## Trigger

User says "작업 구조", "work structure", "팀 구성해줘", or invokes `/work-structure`.

## Purpose

Read a spec document and decompose it into a sub-agent team structure with defined roles, dependencies, and model tiers. Present the plan for user approval, then execute team creation.

## Workflow

### Step 1: Load the Spec

- If the user provides a path, read that spec file
- If no path is provided, list files in `specs/` and use the most recently modified one
- If `specs/` is empty or missing, ask the user which spec to use

### Step 2: Analyze Required Work

Break the spec into distinct work areas:
- What needs to be built (implementation tasks)
- What needs to be validated (testing/QA tasks)
- What information needs to be gathered (research tasks)
- What documentation needs to be written (support tasks)

Cross-reference with `kb/` for relevant cases or principles that should inform agent prompts.

### Step 3: Design the Team

Assign each work area to a named sub-agent with:

| Field | Description |
|-------|-------------|
| **Name** | Short, descriptive identifier (e.g., `api-builder`, `schema-designer`) |
| **Role** | One-line description of responsibility |
| **Model Tier** | `opus`, `sonnet`, or `haiku` (see rules below) |
| **Tasks** | Specific deliverables this agent produces |
| **Dependencies** | Which other agents must complete first |
| **Context** | Key information to inject into the agent's prompt |

#### Model Tier Rules

| Tier | Use For | Examples |
|------|---------|---------|
| `opus` | Strategy, architecture, complex judgment calls | System architect, complex algorithm designer, trade-off analysis |
| `sonnet` | Standard implementation, validation, integration | Feature implementer, QA tester, API builder |
| `haiku` | Information gathering, writing, simple transforms | Researcher, docs writer, data formatter |

### Step 4: Mandatory Agents

Every team MUST include:

1. **QA agent** (`sonnet`) — validates deliverables against the spec's acceptance criteria. List the specific criteria this agent checks.
2. **Support agent** (`haiku`) — handles documentation, README updates, and cleanup tasks.

### Step 5: Present for Approval

Present the team plan as a table:

```
| Agent | Role | Tier | Dependencies | Key Tasks |
|-------|------|------|--------------|-----------|
| ... | ... | ... | ... | ... |
```

Include:
- Total agent count
- Execution order (which agents run in parallel vs. sequential)
- Estimated complexity assessment

Wait for user approval before proceeding.

### Step 6: Execute Team Creation

On user approval, create the team using Claude Code's sub-agent capabilities:
- Inject the spec purpose and relevant sections into each agent's prompt
- Include relevant `kb/` entries as context where applicable
- Set up dependency ordering so agents execute in the correct sequence

## Key Behaviors

- **Right-size the team.** Do not create agents for trivial tasks that can be handled inline. Do not combine unrelated responsibilities into one agent.
- **Inject context, not the whole spec.** Each agent gets only the sections relevant to their role, plus the overall purpose for alignment.
- **Define clear boundaries.** Each agent should know exactly what they own and what they do NOT own. Overlap causes conflicts.
- **Reference acceptance criteria.** The QA agent's validation targets come directly from the spec's Section 3 (Acceptance Criteria).
- **Consider the knowledge base.** If `kb/` contains relevant cases or principles, include them in agent context to inform decision-making.
- **Respect escalation rules.** Areas marked for escalation in the spec's Section 6 (Agent Discretion) must be flagged — agents should not make those decisions autonomously.
