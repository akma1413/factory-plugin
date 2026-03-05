"""Factory Manager — main orchestrator for the agent harness pipeline.

Flow: Load spec -> Inject context -> Decompose -> Execute -> Monitor -> Verify -> Record -> Report

Usage:
    python -m harness.manager specs/my-spec.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from harness.context import (
    extract_tags,
    scan_kb,
    select_context_with_agent,
    format_context,
)
from harness.supervisor import Supervisor
from harness.recorder import Recorder
from harness.verification import verify, VerificationResult


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_ROUNDS = 10  # Hard ceiling on implementation rounds
STAGNATION_LIMIT = 3  # Halt after this many rounds without progress
CLAUDE_BINARY = "claude"


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def load_spec(spec_path: str) -> str:
    """Read and return the spec file contents."""
    path = Path(spec_path)
    if not path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def call_claude(
    prompt: str,
    cwd: str | None = None,
    max_turns: int | None = None,
    timeout: int = 300,
) -> str:
    """Call claude -p (pipe mode) and return the response text.

    Args:
        prompt: The prompt to send to Claude.
        cwd: Working directory for the subprocess.
        max_turns: If set, pass --max-turns to limit tool use.
        timeout: Subprocess timeout in seconds.
    """
    if shutil.which(CLAUDE_BINARY) is None:
        raise FileNotFoundError(
            f"'{CLAUDE_BINARY}' CLI not found. "
            "Install it from https://claude.ai/code or set --claude-binary to the correct path."
        )
    cmd = [CLAUDE_BINARY, "-p", "--output-format", "json"]
    if max_turns is not None:
        cmd.extend(["--max-turns", str(max_turns)])

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )

    if result.returncode != 0:
        error_msg = result.stderr[:500] if result.stderr else "Unknown error"
        raise RuntimeError(
            f"Claude call failed (exit {result.returncode}): {error_msg}"
        )

    # Parse the JSON envelope
    try:
        envelope = json.loads(result.stdout)
        inner = envelope.get("result", result.stdout)
        if isinstance(inner, dict):
            return inner.get("text", str(inner))
        return str(inner)
    except json.JSONDecodeError:
        return result.stdout


def decompose_work(spec_text: str, context: str) -> str:
    """Ask an agent to decompose the spec into a work structure.

    Returns a work plan as markdown text.
    """
    prompt = (
        "You are a work structure planner for a coding project.\n\n"
        f"## Spec\n{spec_text}\n\n"
        f"## Reference Context\n{context}\n\n"
        "Break this spec into a numbered list of implementation steps. "
        "For each step, specify:\n"
        "1. What to do\n"
        "2. Which files to create or modify\n"
        "3. How to verify the step is done\n\n"
        "Return only the work plan as markdown."
    )
    return call_claude(prompt, max_turns=1)


def execute_step(
    spec_text: str,
    context: str,
    work_plan: str,
    project_path: str,
    previous_feedback: str | None = None,
) -> str:
    """Ask an agent to implement the spec according to the work plan.

    Returns the agent's execution log/output.
    """
    prompt_parts = [
        "You are an implementation agent. Execute the work plan below.",
        f"\n## Spec\n{spec_text}",
        f"\n## Reference Context\n{context}",
        f"\n## Work Plan\n{work_plan}",
    ]

    if previous_feedback:
        prompt_parts.append(
            f"\n## Previous Round Feedback\n"
            f"The previous implementation attempt had issues:\n{previous_feedback}\n"
            f"Fix these issues while preserving what already works."
        )

    prompt_parts.append(
        "\nImplement the work plan. Create or modify files as needed. "
        "Explain what you did at the end."
    )

    return call_claude("\n".join(prompt_parts), cwd=project_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    spec_path: str,
    project_path: str,
    max_rounds: int = MAX_ROUNDS,
    claude_binary: str = CLAUDE_BINARY,
) -> None:
    """Run the full Factory Manager pipeline.

    Steps:
    1. Load spec
    2. Inject context from kb/
    3. Decompose into work structure
    4. Execute implementation (with verification loop)
    5. Monitor for pathological patterns
    6. Record all decisions
    7. Output final report
    """
    global CLAUDE_BINARY
    CLAUDE_BINARY = claude_binary

    if shutil.which(CLAUDE_BINARY) is None:
        print(f"ERROR: '{CLAUDE_BINARY}' CLI not found.")
        print(
            "Install it from https://claude.ai/code or use --claude-binary to specify the path."
        )
        sys.exit(1)

    spec_path = str(Path(spec_path).resolve())
    project_path = str(Path(project_path).resolve())

    print("=" * 60)
    print("FACTORY MANAGER — Starting pipeline")
    print(f"  Spec: {spec_path}")
    print(f"  Project: {project_path}")
    print("=" * 60)

    # Initialize components
    recorder = Recorder.create()
    supervisor = Supervisor()

    print(f"\nRun ID: {recorder.run_id}")
    print(f"Logs: {recorder.log_dir}")

    # Step 1: Load spec
    print("\n[1/4] Loading spec...")
    spec_text = load_spec(spec_path)
    recorder.log_decision("manager", "Loaded spec", f"Path: {spec_path}")

    # Step 2: Inject context
    print("[2/4] Injecting context from kb/...")
    tags = extract_tags(spec_path)
    print(f"  Tags extracted: {tags}")

    entries = scan_kb(tags)
    if entries:
        print(f"  Found {len(entries)} matching KB entries")
        # Optionally refine with agent selection
        try:
            entries = select_context_with_agent(spec_path, entries)
            print(f"  Agent selected {len(entries)} entries")
        except Exception:
            print("  Agent selection skipped (falling back to all matches)")

    context = format_context(entries)
    recorder.log_context(entries)
    recorder.log_decision(
        "manager", "Context injected", f"{len(entries)} entries selected"
    )

    # Step 3: Decompose work
    print("[3/4] Decomposing spec into work structure...")
    try:
        work_plan = decompose_work(spec_text, context)
        print("  Work plan generated")
        recorder.log_decision("manager", "Work decomposed", "Agent produced work plan")
    except Exception as e:
        print(f"  ERROR: Work decomposition failed: {e}")
        recorder.log_decision("manager", "Work decomposition failed", str(e))
        recorder.finalize()
        sys.exit(1)

    # Step 4: Execute with verification loop
    print("[4/4] Starting implementation + verification loop...")
    print()

    previous_pass_count = 0
    stagnation_count = 0
    feedback: str | None = None

    for round_num in range(1, max_rounds + 1):
        print(f"--- Round {round_num}/{max_rounds} ---")

        # Execute implementation
        print("  Executing implementation...")
        try:
            execution_log = execute_step(
                spec_text, context, work_plan, project_path, feedback
            )
            supervisor.feed(execution_log)
            recorder.log_decision(
                "implementation_agent",
                f"Round {round_num} execution",
                execution_log[:500],
            )
        except Exception as e:
            print(f"  ERROR: Implementation failed: {e}")
            supervisor.feed(str(e))
            recorder.log_decision(
                "implementation_agent",
                f"Round {round_num} failed",
                str(e),
            )
            feedback = f"Implementation error: {e}"
            continue

        # Check supervisor
        sv_result = supervisor.check()
        if sv_result.pattern:
            print(f"  SUPERVISOR: [{sv_result.severity}] {sv_result.pattern}")
            print(f"    {sv_result.recommendation}")
            recorder.log_decision(
                "supervisor",
                f"Pattern detected: {sv_result.pattern}",
                sv_result.recommendation,
            )
            if sv_result.severity == "critical":
                print("  Supervisor recommends halting — critical pattern detected.")
                break

        # Run verification
        print("  Running verification...")
        try:
            v_result = verify(spec_path, project_path)
        except Exception as e:
            print(f"  ERROR: Verification failed: {e}")
            v_result = VerificationResult(criteria=[])

        recorder.log_verification(round_num, v_result.to_dicts())
        supervisor.record_progress(v_result.pass_count)

        print(f"  Verification: {v_result.pass_count}/{v_result.total} criteria passed")

        # Check if done
        if v_result.all_passed:
            print("\n  ALL CRITERIA PASSED — implementation complete!")
            recorder.log_decision("manager", "Pipeline complete", "All criteria passed")
            break

        # Check for progress
        if v_result.has_progress(previous_pass_count):
            print(f"  Progress: {previous_pass_count} -> {v_result.pass_count} passes")
            stagnation_count = 0
        else:
            stagnation_count += 1
            print(
                f"  No progress (stagnation count: {stagnation_count}/{STAGNATION_LIMIT})"
            )

        if stagnation_count >= STAGNATION_LIMIT:
            print(
                f"\n  HALTING — no progress for {STAGNATION_LIMIT} consecutive rounds."
            )
            recorder.log_decision(
                "manager",
                "Pipeline halted",
                f"No progress for {STAGNATION_LIMIT} rounds",
            )
            break

        # Prepare feedback for next round
        previous_pass_count = v_result.pass_count
        failed = [c for c in v_result.criteria if not c.passed]
        feedback = "The following criteria still fail:\n" + "\n".join(
            f"- {c.id}: {c.description} — {c.details}" for c in failed
        )
        print()

    else:
        print(f"\n  HALTING — reached maximum rounds ({max_rounds}).")
        recorder.log_decision(
            "manager", "Pipeline halted", f"Reached max rounds ({max_rounds})"
        )

    # Finalize
    print()
    print("=" * 60)
    summary_path = recorder.finalize()
    print(f"FACTORY MANAGER — Pipeline finished")
    print(f"  Summary: {summary_path}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the Factory Manager."""
    parser = argparse.ArgumentParser(
        prog="factory-manager",
        description="Factory Manager — autonomous agent harness pipeline",
    )
    parser.add_argument(
        "spec",
        help="Path to the spec file (e.g., specs/my-spec.md)",
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Path to the project root (default: current directory)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=MAX_ROUNDS,
        help=f"Maximum implementation rounds (default: {MAX_ROUNDS})",
    )
    parser.add_argument(
        "--claude-binary",
        default=CLAUDE_BINARY,
        help=f"Path to claude CLI binary (default: {CLAUDE_BINARY})",
    )

    args = parser.parse_args()

    run_pipeline(
        args.spec,
        args.project_path,
        max_rounds=args.max_rounds,
        claude_binary=args.claude_binary,
    )


if __name__ == "__main__":
    main()
