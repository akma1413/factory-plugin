#!/bin/bash
# Tool mediation hook — called by Claude Code before each Bash tool execution.
# Stdin: JSON with tool_name and tool_input fields.
# Exit 0: allow the tool call.
# Exit 2: block the tool call (stderr message shown to agent).

INPUT=$(cat)

# Extract the command from the tool_input JSON
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', data.get('input', {}))
    print(tool_input.get('command', ''))
except Exception:
    print('')
")

# Block catastrophically destructive commands
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/($|\s|")'; then
    echo "BLOCKED: Attempted to run: rm -rf /" >&2
    echo "This command would destroy the root filesystem." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+~($|\s|")'; then
    echo "BLOCKED: Attempted to run: rm -rf ~" >&2
    echo "This command would destroy the home directory." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+\*($|\s)'; then
    echo "BLOCKED: rm -rf * is too broad to allow safely." >&2
    exit 2
fi

# Warn on force push (allow but print warning to stderr)
if echo "$COMMAND" | grep -q 'push.*--force\|push.*-f'; then
    echo "WARNING: Force push detected. Ensure this is intentional." >&2
    # Allow it (exit 0 falls through)
fi

# Allow everything else
exit 0
