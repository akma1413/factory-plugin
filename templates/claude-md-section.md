## Factory Agent Harness

### Harness Components
| Component | Role |
|---|---|
| Design Skill | Extracts user intent through structured questioning |
| Work Structure Skill | Decomposes spec into sub-agent teams |
| Verification Hook | Intercepts "done" signals and forces quality checks |
| Supervisor | Watches for agents going in circles |
| Recorder | Logs every decision for post-review |
| Reference Library | `kb/` directory with cases and principles |

### Escalation Criteria
Always ask the user before proceeding when:
- The action is **irreversible**
- The change is **user-facing**
- The design decision is **uncertain**

### Translation Obligation
When presenting technical choices, always explain in **business/UX impact terms**.

### Progress Tracking
- `PLAN.md` — what needs to be done
- `PROGRESS.md` — where we left off
