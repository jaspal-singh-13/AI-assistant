"""Guardrails validator classes — heuristic implementations.

Used by output_guard.py Stage 1.
Validators: ToxicLanguage, DetectPII, RestrictToTopic.

FR-GRD-03 Stage 1.
Note: guardrails-ai is not installable as a pip package (broken dep chain),
so these are standalone heuristic validators with the same interface.
"""

from __future__ import annotations

import re

_TOXIC_PATTERNS = re.compile(
    r"\b(kill\s+yourself|kys|go\s+die|die\s+in\s+a\s+fire|"
    r"subhuman|vermin|parasite|filth|scum|trash|worthless\s+piece|"
    r"i\s+hope\s+you\s+die|you\s+should\s+die)\b",
    re.IGNORECASE,
)

_PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.IGNORECASE),
    "PHONE": re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

_OFF_TOPIC_PATTERNS = re.compile(
    r"\b(make\s+a\s+bomb|synthesize\s+(drugs?|meth|fentanyl)|hack\s+into|"
    r"ddos|ransomware|malware|exploit\s+vulnerability|phishing\s+attack)\b",
    re.IGNORECASE,
)


class ToxicLanguage:
    """Detect profanity, slurs, and dehumanising language."""

    def validate(self, value: str) -> tuple[bool, str | None]:
        """Return (passed, reason). passed=True means safe."""
        if _TOXIC_PATTERNS.search(value):
            return False, "toxic_language_detected"
        return True, None


class DetectPII:
    """Detect PII in output text (informational — caller decides whether to block)."""

    def validate(self, value: str) -> tuple[bool, list[dict]]:
        """Return (passed, entities). passed=True means no PII found."""
        found = []
        for entity_type, pattern in _PII_PATTERNS.items():
            for m in pattern.finditer(value):
                found.append({"entity_type": entity_type, "start": m.start(), "end": m.end()})
        return len(found) == 0, found


class RestrictToTopic:
    """Detect responses that drift into clearly off-topic harmful territory."""

    def validate(self, value: str) -> tuple[bool, str | None]:
        """Return (passed, reason). passed=True means on-topic."""
        if _OFF_TOPIC_PATTERNS.search(value):
            return False, "off_topic_harmful_content"
        return True, None
