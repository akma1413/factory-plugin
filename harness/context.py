"""Context injection module — finds relevant KB entries for a spec."""

from __future__ import annotations

import re
import subprocess
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> dict[str, str | list[str]]:
    """Parse YAML-like frontmatter between --- markers.

    Supports simple key: value pairs and key: [a, b, c] lists.
    Uses only stdlib — no pyyaml dependency.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    meta: dict[str, str | list[str]] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        # Handle [a, b, c] list syntax
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            meta[key.strip()] = [i for i in items if i]
        else:
            meta[key.strip()] = value.strip("'\"")
    return meta


def _body_without_frontmatter(text: str) -> str:
    """Return the markdown body with frontmatter stripped."""
    return re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_tags(spec_path: str) -> list[str]:
    """Extract topic tags from a spec file.

    Looks for:
    - Frontmatter `tags:` field
    - Section headings and bold keywords as implicit topics
    """
    text = Path(spec_path).read_text(encoding="utf-8")

    # Try frontmatter tags first
    meta = _parse_frontmatter(text)
    if "tags" in meta:
        raw = meta["tags"]
        if isinstance(raw, list):
            return [t.lower() for t in raw]
        return [t.strip().lower() for t in str(raw).split(",")]

    # Fallback: extract meaningful words from headings and bold text
    tags: list[str] = []
    body = _body_without_frontmatter(text)

    # Heading words (## Foo Bar → foo, bar)
    for heading in re.findall(r"^#{1,3}\s+(.+)$", body, re.MULTILINE):
        for word in re.findall(r"[a-zA-Z][\w-]+", heading):
            tag = word.lower()
            if tag not in _STOP_WORDS and tag not in tags:
                tags.append(tag)

    # Bold words (**term**)
    for bold in re.findall(r"\*\*(.+?)\*\*", body):
        for word in re.findall(r"[a-zA-Z][\w-]+", bold):
            tag = word.lower()
            if tag not in _STOP_WORDS and tag not in tags:
                tags.append(tag)

    return tags


# Words too generic to be useful as tags
_STOP_WORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "this",
        "that",
        "with",
        "from",
        "are",
        "not",
        "must",
        "should",
        "will",
        "may",
        "can",
        "has",
        "have",
        "been",
        "what",
        "when",
        "where",
        "how",
        "why",
        "who",
        "which",
        "spec",
        "criterion",
        "criteria",
        "priority",
        "constraint",
        "agent",
        "discretion",
        "area",
        "purpose",
        "expected",
        "outcome",
        "acceptance",
        "title",
        "section",
        "example",
        "specific",
        "testable",
        "condition",
        "non",
        "negotiable",
        "requirements",
        "things",
        "avoid",
        "highest",
        "guidance",
        "escalation",
    }
)


def scan_kb(tags: list[str], kb_root: str | None = None) -> list[dict]:
    """Scan kb/cases/ and kb/principles/ for entries matching any tag.

    When kb_root is None, scans both project KB (cwd/kb) and global KB
    (~/.factory/kb), merging results with project entries taking priority.
    Returns a list of dicts: {path, title, tags, content}.
    """
    tag_set = {t.lower() for t in tags}

    # Determine which KB roots to scan (project first for priority)
    if kb_root is not None:
        kb_roots = [Path(kb_root)]
    else:
        kb_roots = [Path.cwd() / "kb", Path.home() / ".factory" / "kb"]

    seen_rel_paths: set[str] = set()
    results: list[dict] = []

    for root in kb_roots:
        for subdir in ("cases", "principles"):
            dirpath = root / subdir
            if not dirpath.is_dir():
                continue
            for entry_path in sorted(dirpath.rglob("*.md")):
                text = entry_path.read_text(encoding="utf-8")
                meta = _parse_frontmatter(text)

                # Collect entry tags from frontmatter
                entry_tags_raw = meta.get("tags", [])
                if isinstance(entry_tags_raw, str):
                    entry_tags_raw = [t.strip() for t in entry_tags_raw.split(",")]
                entry_tags = [t.lower() for t in entry_tags_raw]

                # Also consider the title as an implicit tag
                title = str(meta.get("title", entry_path.stem))

                # Match if any tag overlaps; project entries take priority on duplicates
                rel_key = str(entry_path.relative_to(root))
                all_entry_keywords = set(entry_tags) | {title.lower()}
                if tag_set & all_entry_keywords and rel_key not in seen_rel_paths:
                    seen_rel_paths.add(rel_key)
                    results.append(
                        {
                            "path": str(entry_path),
                            "title": title,
                            "tags": entry_tags,
                            "content": _body_without_frontmatter(text),
                        }
                    )

    return results


def format_context(entries: list[dict]) -> str:
    """Format matched KB entries into an injectable context block."""
    if not entries:
        return "<!-- No relevant knowledge base entries found. -->"

    lines = ["# Reference Context (from kb/)", ""]
    for entry in entries:
        lines.append(f"## {entry['title']}")
        lines.append(f"_Source: {entry['path']}_  ")
        lines.append(f"_Tags: {', '.join(entry['tags'])}_")
        lines.append("")
        lines.append(entry["content"].strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def inject_context(spec_path: str, kb_root: str | None = None) -> str:
    """Main entry point: given a spec, return a context string from kb/.

    Steps:
    1. Extract tags from the spec
    2. Scan KB for matching entries
    3. Format into a context block
    """
    tags = extract_tags(spec_path)
    if not tags:
        return "<!-- No tags extracted from spec — skipping context injection. -->"

    entries = scan_kb(tags, kb_root=kb_root)
    return format_context(entries)


# ---------------------------------------------------------------------------
# Optional: agent-assisted context selection
# ---------------------------------------------------------------------------


def select_context_with_agent(
    spec_path: str,
    entries: list[dict],
    claude_binary: str = "claude",
) -> list[dict]:
    """Use claude -p to pick the most relevant entries from a candidate set.

    Falls back to returning all entries if the agent call fails.
    """
    if not entries:
        return entries

    spec_text = Path(spec_path).read_text(encoding="utf-8")
    entry_summaries = "\n".join(
        f"[{i}] {e['title']} (tags: {', '.join(e['tags'])})"
        for i, e in enumerate(entries)
    )

    prompt = (
        "You are selecting reference materials for a coding task.\n\n"
        f"## Spec\n{spec_text}\n\n"
        f"## Candidate Entries\n{entry_summaries}\n\n"
        "Return ONLY a JSON array of the entry indices (integers) that are "
        "most relevant to this spec. Example: [0, 2, 5]\n"
        "If all are relevant, return all indices. If none, return []."
    )

    try:
        result = subprocess.run(
            [claude_binary, "-p", "--max-turns", "1", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return entries

        # Parse agent response
        response = json.loads(result.stdout)
        text = response.get("result", result.stdout)
        if isinstance(text, dict):
            text = text.get("text", str(text))
        # Extract JSON array from response
        match = re.search(r"\[[\d\s,]*\]", str(text))
        if match:
            indices = json.loads(match.group())
            return [entries[i] for i in indices if 0 <= i < len(entries)]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass  # Fall back to returning all entries

    return entries
