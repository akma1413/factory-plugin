"""Supervisor module — detects pathological agent behavior patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class SupervisorResult:
    """Result of a supervisor check."""

    pattern: str | None  # Name of the detected pattern, or None if healthy
    severity: str  # "ok", "warning", "critical"
    recommendation: str  # Human-readable advice


@dataclass
class Supervisor:
    """Monitors agent execution and detects problematic patterns.

    Patterns detected:
    - Stagnation: same error repeated 3+ times
    - Oscillation: fix-break-fix-break cycle
    - Runaway: output growing without progress on criteria
    - Token waste: excessive output with no measurable improvement
    """

    window_size: int = 20
    stagnation_threshold: int = 3
    similarity_cutoff: float = 0.85

    _log_entries: list[str] = field(default_factory=list, repr=False)
    _criteria_progress: list[int] = field(default_factory=list, repr=False)

    def feed(self, log_entry: str) -> None:
        """Receive a new log entry from the agent execution."""
        self._log_entries.append(log_entry)
        # Keep only the sliding window
        if len(self._log_entries) > self.window_size:
            self._log_entries = self._log_entries[-self.window_size :]

    def record_progress(self, pass_count: int) -> None:
        """Record how many acceptance criteria passed this round."""
        self._criteria_progress.append(pass_count)

    def check(self) -> SupervisorResult:
        """Analyze current state and return the most severe pattern found."""
        checks = [
            self._check_oscillation,
            self._check_stagnation,
            self._check_runaway,
            self._check_token_waste,
        ]
        worst: SupervisorResult | None = None
        severity_rank = {"ok": 0, "warning": 1, "critical": 2}

        for check_fn in checks:
            result = check_fn()
            if (
                worst is None
                or severity_rank[result.severity] > severity_rank[worst.severity]
            ):
                worst = result

        return worst or SupervisorResult(
            pattern=None, severity="ok", recommendation="Agent is operating normally."
        )

    def reset(self) -> None:
        """Clear state for a new monitoring session."""
        self._log_entries.clear()
        self._criteria_progress.clear()

    # ------------------------------------------------------------------
    # Pattern detectors
    # ------------------------------------------------------------------

    def _check_stagnation(self) -> SupervisorResult:
        """Detect repeated identical or near-identical log entries."""
        if len(self._log_entries) < self.stagnation_threshold:
            return SupervisorResult(None, "ok", "Not enough data to detect stagnation.")

        recent = self._log_entries[-self.stagnation_threshold :]
        # Check if all recent entries are similar to each other
        all_similar = all(
            _similarity(recent[0], entry) >= self.similarity_cutoff
            for entry in recent[1:]
        )

        if all_similar:
            return SupervisorResult(
                pattern="stagnation",
                severity="critical",
                recommendation=(
                    f"Agent appears stuck — the last {self.stagnation_threshold} log entries "
                    f"are nearly identical. Consider changing approach or escalating."
                ),
            )
        return SupervisorResult(None, "ok", "No stagnation detected.")

    def _check_oscillation(self) -> SupervisorResult:
        """Detect fix-break-fix-break cycles (A→B→A→B pattern)."""
        if len(self._log_entries) < 4:
            return SupervisorResult(
                None, "ok", "Not enough data to detect oscillation."
            )

        # Check last 4 entries for A-B-A-B pattern
        entries = self._log_entries[-4:]
        a_match = _similarity(entries[0], entries[2]) >= self.similarity_cutoff
        b_match = _similarity(entries[1], entries[3]) >= self.similarity_cutoff
        a_b_different = _similarity(entries[0], entries[1]) < self.similarity_cutoff

        if a_match and b_match and a_b_different:
            return SupervisorResult(
                pattern="oscillation",
                severity="critical",
                recommendation=(
                    "Agent is oscillating between two states (fix → break → fix → break). "
                    "The current approach is not converging. Needs a fundamentally "
                    "different strategy."
                ),
            )
        return SupervisorResult(None, "ok", "No oscillation detected.")

    def _check_runaway(self) -> SupervisorResult:
        """Detect implementation growing beyond spec scope."""
        if len(self._criteria_progress) < 2:
            return SupervisorResult(None, "ok", "Not enough rounds to detect runaway.")

        # If output is growing but criteria progress is flat
        recent_progress = (
            self._criteria_progress[-3:]
            if len(self._criteria_progress) >= 3
            else self._criteria_progress
        )
        no_progress = len(set(recent_progress)) == 1  # All same value

        if no_progress and len(self._log_entries) > self.window_size // 2:
            return SupervisorResult(
                pattern="runaway",
                severity="warning",
                recommendation=(
                    "Agent is producing output but acceptance criteria progress is flat. "
                    "May be working on things outside spec scope. Consider re-focusing."
                ),
            )
        return SupervisorResult(None, "ok", "No runaway detected.")

    def _check_token_waste(self) -> SupervisorResult:
        """Detect excessive output without measurable progress."""
        if len(self._log_entries) < 5:
            return SupervisorResult(
                None, "ok", "Not enough data to detect token waste."
            )

        # Check if recent entries are very long but criteria aren't improving
        recent = self._log_entries[-5:]
        total_length = sum(len(e) for e in recent)
        avg_length = total_length / len(recent)

        has_progress = (
            len(self._criteria_progress) >= 2
            and self._criteria_progress[-1] > self._criteria_progress[-2]
        )

        if avg_length > 2000 and not has_progress:
            return SupervisorResult(
                pattern="token_waste",
                severity="warning",
                recommendation=(
                    "Agent is generating verbose output without improving pass rate. "
                    "Consider asking for a more targeted approach."
                ),
            )
        return SupervisorResult(None, "ok", "No token waste detected.")


def _similarity(a: str, b: str) -> float:
    """Compute string similarity ratio between two texts (0.0 to 1.0)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def detect_loop(log_entries: list[str], criteria_progress: list[int]) -> str | None:
    supervisor = Supervisor()
    for entry in log_entries:
        supervisor.feed(entry)
    for progress in criteria_progress:
        supervisor.record_progress(progress)
    result = supervisor.check()
    return result.pattern
