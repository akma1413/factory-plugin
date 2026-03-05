from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import cast


@dataclass
class Criterion:
    id: str
    description: str
    passed: bool = False
    details: str = ""
    verdict: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class VerificationResult:
    criteria: list[Criterion]
    all_passed: bool = False
    pass_count: int = 0
    total: int = 0

    def __post_init__(self) -> None:
        self.total = len(self.criteria)
        self.pass_count = sum(1 for criterion in self.criteria if criterion.passed)
        self.all_passed = self.total > 0 and self.pass_count == self.total

    def to_dicts(self) -> list[dict[str, object]]:
        return [
            {
                "id": criterion.id,
                "description": criterion.description,
                "passed": criterion.passed,
                "details": criterion.details,
                "verdict": criterion.verdict,
                "confidence": criterion.confidence,
                "evidence": list(criterion.evidence),
                "reason": criterion.reason,
            }
            for criterion in self.criteria
        ]

    def has_progress(self, previous_pass_count: int) -> bool:
        return self.pass_count > previous_pass_count

    def to_llm_verdicts(self) -> list[object]:
        try:
            from harness.recorder import LLMVerdict

            return [
                LLMVerdict(
                    criterion_id=criterion.id,
                    verdict=criterion.verdict
                    or ("pass" if criterion.passed else "fail"),
                    confidence=criterion.confidence,
                    evidence=list(criterion.evidence),
                    reason=criterion.reason or criterion.details,
                )
                for criterion in self.criteria
            ]
        except ImportError:
            return [
                SimpleNamespace(
                    criterion_id=criterion.id,
                    verdict=criterion.verdict
                    or ("pass" if criterion.passed else "fail"),
                    confidence=criterion.confidence,
                    evidence=list(criterion.evidence),
                    reason=criterion.reason or criterion.details,
                )
                for criterion in self.criteria
            ]


def parse_criteria(spec_path: str) -> list[Criterion]:
    text = Path(spec_path).read_text(encoding="utf-8")

    criteria_section = _extract_section(text, "Acceptance Criteria")
    if not criteria_section:
        criteria_section = text

    criteria: list[Criterion] = []
    pattern = re.compile(r"^-\s+\[[ x]\]\s+(.+)$", re.MULTILINE | re.IGNORECASE)

    for index, match in enumerate(pattern.finditer(criteria_section), start=1):
        description = match.group(1).strip()
        id_match = re.match(r"(?:Criterion\s+)?(\d+)[:.]\s*(.*)", description)
        if id_match:
            criteria.append(
                Criterion(
                    id=f"C{id_match.group(1)}",
                    description=id_match.group(2),
                )
            )
        else:
            criteria.append(
                Criterion(
                    id=f"C{index}",
                    description=description,
                )
            )

    return criteria


def verify(
    spec_path: str,
    project_path: str,
    claude_binary: str = "claude",
) -> VerificationResult:
    criteria = parse_criteria(spec_path)
    if not criteria:
        return VerificationResult(criteria=[])

    spec_text = Path(spec_path).read_text(encoding="utf-8")
    criteria_list = "\n".join(
        f"{criterion.id}: {criterion.description}" for criterion in criteria
    )

    prompt = (
        "You are a verification agent. Check whether the codebase meets "
        "each acceptance criterion.\n\n"
        f"## Spec\n{spec_text}\n\n"
        f"## Project Path\n{project_path}\n\n"
        f"## Acceptance Criteria to Verify\n{criteria_list}\n\n"
        "For EACH criterion, evaluate whether it is met by examining project files "
        "and command output. Return a JSON array where each element has:\n"
        "  - id: criterion ID\n"
        "  - verdict: pass | fail | abstain\n"
        "  - confidence: float from 0.0 to 1.0\n"
        "  - evidence: list of concrete evidence (file paths and/or command output)\n"
        "  - reason: concise explanation\n\n"
        "If no concrete evidence is found, set verdict to abstain.\n\n"
        "Return ONLY the JSON array, no other text."
    )

    try:
        result = subprocess.run(
            [claude_binary, "-p", "--max-turns", "1", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_path,
        )

        if result.returncode != 0:
            for criterion in criteria:
                criterion.details = f"Verification agent failed: {result.stderr[:200]}"
            return VerificationResult(criteria=criteria)

        response_text = result.stdout
        try:
            envelope_obj = cast(object, json.loads(response_text))
            inner_obj: object = response_text
            envelope = _normalize_mapping(envelope_obj)
            if envelope is not None:
                inner_obj = envelope.get("result", response_text)

            inner = _normalize_mapping(inner_obj)
            if inner is not None:
                inner_obj = inner.get("text", str(inner_obj))

            response_text = str(inner_obj)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if match:
            results_obj = cast(object, json.loads(match.group()))
            parsed_results = _normalize_result_list(results_obj)
            if parsed_results is not None:
                apply_verification_results(criteria, parsed_results)
            else:
                for criterion in criteria:
                    criterion.details = "Could not parse verification agent response."
        else:
            for criterion in criteria:
                criterion.details = "Could not parse verification agent response."

    except subprocess.TimeoutExpired:
        for criterion in criteria:
            criterion.details = "Verification agent timed out."
    except Exception as error:
        for criterion in criteria:
            criterion.details = f"Verification error: {error}"

    return VerificationResult(criteria=criteria)


def apply_verification_results(
    criteria: list[Criterion], results_data: list[dict[str, object]]
) -> None:
    results_map: dict[str, dict[str, object]] = {}
    for item in results_data:
        item_id = item.get("id")
        if isinstance(item_id, str):
            results_map[item_id] = item

    for criterion in criteria:
        result_data = results_map.get(criterion.id)
        if result_data is None:
            criterion.details = "Not evaluated by verification agent."
            continue
        _apply_result_data(criterion, result_data)


def _apply_result_data(criterion: Criterion, data: dict[str, object]) -> None:
    raw_verdict = str(data.get("verdict", "")).strip().lower()
    verdict = raw_verdict if raw_verdict in {"pass", "fail", "abstain"} else ""

    if verdict:
        criterion.verdict = verdict
        criterion.passed = verdict == "pass"
    else:
        criterion.passed = bool(data.get("passed", False))
        criterion.verdict = "pass" if criterion.passed else "fail"

    confidence_value = data.get("confidence", 0.0)
    if isinstance(confidence_value, (int, float, str)):
        try:
            confidence = float(confidence_value)
        except ValueError:
            confidence = 0.0
    else:
        confidence = 0.0
    criterion.confidence = max(0.0, min(1.0, confidence))

    evidence_value = data.get("evidence", [])
    if isinstance(evidence_value, list):
        evidence_items = cast(list[object], evidence_value)
        criterion.evidence = [str(item) for item in evidence_items if str(item).strip()]
    elif evidence_value:
        criterion.evidence = [str(evidence_value)]
    else:
        criterion.evidence = []

    criterion.details = str(data.get("details", ""))
    criterion.reason = str(data.get("reason", "")).strip() or criterion.details
    if not criterion.details:
        criterion.details = criterion.reason

    if criterion.verdict != "pass" and not criterion.evidence:
        criterion.verdict = "abstain"
        criterion.confidence = 0.0
        criterion.passed = False


def _normalize_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None

    normalized: dict[str, object] = {}
    for key, item in cast(dict[object, object], value).items():
        normalized[str(key)] = item
    return normalized


def _normalize_result_list(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None

    normalized: list[dict[str, object]] = []
    for item in cast(list[object], value):
        mapping = _normalize_mapping(item)
        if mapping is not None:
            normalized.append(mapping)
    return normalized


def _extract_section(text: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"^(#{{1,3}})\s+.*{re.escape(heading)}.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None

    level = len(match.group(1))
    start = match.end()

    next_heading = re.compile(rf"^#{{{1},{level}}}\s+", re.MULTILINE)
    next_match = next_heading.search(text, start)
    if next_match:
        return text[start : next_match.start()]
    return text[start:]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m harness.verification <spec_path> [project_path]")
        sys.exit(1)

    spec_path = sys.argv[1]
    project_path = sys.argv[2] if len(sys.argv) > 2 else str(Path.cwd())

    if not Path(spec_path).exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)

    print(f"Verifying spec: {spec_path}")
    print(f"Project path: {project_path}")
    print()

    result = verify(spec_path, project_path)

    for criterion in result.criteria:
        status = "PASS" if criterion.passed else "FAIL"
        print(f"  [{status}] {criterion.id}: {criterion.description}")
        if criterion.details:
            print(f"         {criterion.details}")

    print()
    print(f"Result: {result.pass_count}/{result.total} criteria passed")
    sys.exit(0 if result.all_passed else 1)


if __name__ == "__main__":
    main()
