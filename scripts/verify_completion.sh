#!/usr/bin/env bash
# Called by Claude Code hook system when agent signals completion.
# Runs verification against the spec's acceptance criteria.
#
# Usage: scripts/verify_completion.sh <spec_path> [project_path]

SPEC_PATH="${1:-}"
PROJECT_PATH="${2:-$(pwd)}"

if [ -z "$SPEC_PATH" ]; then
    echo "ERROR: No spec path provided"
    echo "Usage: scripts/verify_completion.sh <spec_path> [project_path]"
    exit 1
fi

if [ ! -f "$SPEC_PATH" ]; then
    echo "ERROR: Spec file not found: $SPEC_PATH"
    exit 1
fi

# Run verification - PYTHONPATH points to plugin root so bundled harness is found
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m harness.verification "$SPEC_PATH" "$PROJECT_PATH"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "VERIFICATION PASSED — all acceptance criteria met"
    exit 0
else
    echo "VERIFICATION FAILED — see output above for details"
    exit 1
fi
