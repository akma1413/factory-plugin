"""Recorder module — logs every decision for post-run review."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Recorder:
    """Records decisions, context, verification results, and design changes.

    Creates a timestamped log directory under logs/ and writes structured
    markdown files for post-run review.
    """

    run_id: str
    log_dir: Path = field(init=False)

    _decisions: list[dict] = field(default_factory=list, repr=False)
    _verifications: list[dict] = field(default_factory=list, repr=False)
    _changes: list[dict] = field(default_factory=list, repr=False)
    _context_entries: list[dict] = field(default_factory=list, repr=False)
    _start_time: datetime = field(default_factory=datetime.now, repr=False)

    def __post_init__(self) -> None:
        project_root = Path.cwd()
        self.log_dir = project_root / "logs" / self.run_id
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls) -> "Recorder":
        """Create a new recorder with a timestamp-based run ID."""
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        return cls(run_id=run_id)

    # ------------------------------------------------------------------
    # Logging methods
    # ------------------------------------------------------------------

    def log_decision(self, agent: str, decision: str, rationale: str) -> None:
        """Log a decision made by an agent."""
        self._decisions.append({
            "timestamp": _now(),
            "agent": agent,
            "decision": decision,
            "rationale": rationale,
        })

    def log_context(self, entries: list[dict]) -> None:
        """Log which reference materials were consulted."""
        self._context_entries = entries

    def log_verification(self, round_num: int, results: list[dict]) -> None:
        """Log verification results for a round.

        Each result dict should have: {id, description, passed, details}.
        """
        self._verifications.append({
            "round": round_num,
            "timestamp": _now(),
            "results": results,
        })

    def log_design_change(self, what: str, why: str, spec_alignment: str) -> None:
        """Log an autonomous design change."""
        self._changes.append({
            "timestamp": _now(),
            "what": what,
            "why": why,
            "spec_alignment": spec_alignment,
        })

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def finalize(self) -> str:
        """Write all log files and return the summary path."""
        self._write_decisions()
        self._write_verification()
        self._write_changes()
        summary_path = self._write_summary()
        return str(summary_path)

    def _write_decisions(self) -> None:
        """Write decisions.md."""
        lines = ["# Decision Trace", ""]
        if not self._decisions:
            lines.append("No decisions recorded.")
        else:
            for d in self._decisions:
                lines.append(f"## [{d['timestamp']}] {d['agent']}")
                lines.append(f"**Decision**: {d['decision']}")
                lines.append(f"**Rationale**: {d['rationale']}")
                lines.append("")

        if self._context_entries:
            lines.append("---")
            lines.append("")
            lines.append("# Reference Materials Consulted")
            lines.append("")
            for entry in self._context_entries:
                title = entry.get("title", "Unknown")
                path = entry.get("path", "")
                tags = ", ".join(entry.get("tags", []))
                lines.append(f"- **{title}** ({path}) — tags: {tags}")
            lines.append("")

        (self.log_dir / "decisions.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_verification(self) -> None:
        """Write verification.md."""
        lines = ["# Verification Results", ""]
        if not self._verifications:
            lines.append("No verification rounds recorded.")
        else:
            for v in self._verifications:
                lines.append(f"## Round {v['round']} ({v['timestamp']})")
                lines.append("")
                passed = sum(1 for r in v["results"] if r.get("passed"))
                total = len(v["results"])
                lines.append(f"**Result**: {passed}/{total} criteria passed")
                lines.append("")
                for r in v["results"]:
                    status = "PASS" if r.get("passed") else "FAIL"
                    lines.append(f"- [{status}] {r.get('id', '?')}: {r.get('description', '')}")
                    if r.get("details"):
                        lines.append(f"  - {r['details']}")
                lines.append("")

        (self.log_dir / "verification.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_changes(self) -> None:
        """Write changes.md."""
        lines = ["# Design Changes (Autonomous)", ""]
        if not self._changes:
            lines.append("No autonomous design changes were made.")
        else:
            for c in self._changes:
                lines.append(f"## [{c['timestamp']}] {c['what']}")
                lines.append(f"**Why**: {c['why']}")
                lines.append(f"**Spec alignment**: {c['spec_alignment']}")
                lines.append("")

        (self.log_dir / "changes.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_summary(self) -> Path:
        """Write summary.md with overall stats."""
        elapsed = datetime.now() - self._start_time
        total_decisions = len(self._decisions)
        total_rounds = len(self._verifications)
        total_changes = len(self._changes)

        # Calculate final pass rate
        final_pass_rate = "N/A"
        if self._verifications:
            last = self._verifications[-1]
            passed = sum(1 for r in last["results"] if r.get("passed"))
            total = len(last["results"])
            final_pass_rate = f"{passed}/{total}"

        lines = [
            "# Run Summary",
            "",
            f"**Run ID**: {self.run_id}",
            f"**Duration**: {elapsed}",
            f"**Decisions logged**: {total_decisions}",
            f"**Verification rounds**: {total_rounds}",
            f"**Design changes**: {total_changes}",
            f"**Final pass rate**: {final_pass_rate}",
            "",
            "## Files",
            "",
            f"- `{self.log_dir}/decisions.md` — decision trace",
            f"- `{self.log_dir}/verification.md` — verification results per round",
            f"- `{self.log_dir}/changes.md` — autonomous design changes",
            f"- `{self.log_dir}/summary.md` — this file",
        ]

        summary_path = self.log_dir / "summary.md"
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        return summary_path


def _now() -> str:
    """Return current timestamp as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
