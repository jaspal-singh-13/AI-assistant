"""Guardrails AI validator classes.

Used by output_guard.py Stage 1.
Validators: ToxicLanguage, DetectPII, RestrictToTopic.

FR-GRD-03 Stage 1.
"""

from __future__ import annotations

# TODO (Phase 3): implement validators using guardrails-ai library.
# Each validator is a guardrails.validators.Validator subclass.
#
# from guardrails.validators import Validator, register_validator, ValidationResult, PassResult, FailResult
#
# @register_validator(name="toxic-language", data_type="string")
# class ToxicLanguage(Validator):
#     def validate(self, value: str, metadata: dict) -> ValidationResult:
#         # TODO: check for profanity, slurs, dehumanising language
#         raise NotImplementedError
#
# @register_validator(name="detect-pii", data_type="string")
# class DetectPII(Validator):
#     def validate(self, value: str, metadata: dict) -> ValidationResult:
#         # TODO: use presidio to detect PII in output
#         raise NotImplementedError
#
# @register_validator(name="restrict-to-topic", data_type="string")
# class RestrictToTopic(Validator):
#     ALLOWED_TOPICS = ["general assistant", "factual questions", "coding help", "analysis"]
#     def validate(self, value: str, metadata: dict) -> ValidationResult:
#         # TODO: detect off-topic drift
#         raise NotImplementedError


class ToxicLanguage:
    """Stub — Phase 3."""


class DetectPII:
    """Stub — Phase 3."""


class RestrictToTopic:
    """Stub — Phase 3."""
