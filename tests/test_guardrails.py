"""Unit tests for guardrails — mocked LlamaGuard, Presidio PII detection.

FR §15.4 + AC §9.4.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


class TestLlamaGuard:
    def test_safe_text_returns_unblocked(self):
        """Safe text returns GuardResult(blocked=False)."""
        pytest.skip("Phase 3")

    def test_hate_speech_blocked_with_category(self):
        """Hate speech returns GuardResult(blocked=True, category='Hate')."""
        pytest.skip("Phase 3")

    def test_category_map_completeness(self):
        """All 13 S-codes are present in CATEGORY_MAP."""
        from guardrails.llamaguard import CATEGORY_MAP
        expected = {f"S{i}" for i in range(1, 14)}
        assert expected == set(CATEGORY_MAP.keys())


class TestInputPipeline:
    def test_prompt_injection_blocked_at_rebuff(self):
        """DAN prompt blocked at Stage 1 (Rebuff) with reason='prompt_injection'."""
        pytest.skip("Phase 3")

    def test_pii_not_blocked_but_logged(self):
        """Message with PII passes through but pii_entities is populated."""
        pytest.skip("Phase 3")

    def test_message_hash_is_sha256(self):
        """message_hash returns a 64-char hex string."""
        from guardrails.input_guard import message_hash
        h = message_hash("test message")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestOutputPipeline:
    def test_toxic_output_blocked(self):
        """Toxic output returns GuardResult(blocked=True)."""
        pytest.skip("Phase 3")

    def test_safe_output_passes(self):
        """Normal helpful response is not blocked."""
        pytest.skip("Phase 3")
