"""Closed vocabularies for decisions: outcomes, rejection reasons, text flags.

Why closed enums: experiment reports count these (ADR-0014 section 5), and a
free-text reason would make counts incomparable between runs and versions.
Adding a member is a contract change.
"""

from enum import StrEnum, unique


@unique
class Outcome(StrEnum):
    """Exactly one per decision (ADR-0013 section 8).

    ``VALID``, ``PARTIAL`` and ``INVALID`` come from validating a reply. The
    other five come from the provider call and are recorded by
    ``record_failure``. ``INVALID`` also covers text that was not JSON at all.
    """

    VALID = "VALID"  # everything in the reply was accepted (text may be truncated)
    PARTIAL = "PARTIAL"  # the reply was current and well formed; some items were dropped
    INVALID = "INVALID"  # nothing from the reply was applied
    REFUSAL = "REFUSAL"
    TRUNCATED = "TRUNCATED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    BUDGET = "BUDGET"


@unique
class Reason(StrEnum):
    """Why a reply or one of its items was rejected (research note 50 section 3).

    Reported to the mind in ``last_results``. A thing the civilization has not
    perceived is reported as ``UNKNOWN_ENTITY`` so a rejection never reveals
    hidden truth.
    """

    SCHEMA_INVALID = "SCHEMA_INVALID"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
    UNAUTHORIZED = "UNAUTHORIZED"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    DUPLICATE_DECISION = "DUPLICATE_DECISION"
    INSUFFICIENT_LABOR = "INSUFFICIENT_LABOR"
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    PREREQ_PROCESS_UNAVAILABLE = "PREREQ_PROCESS_UNAVAILABLE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    ILLEGAL_TERRAIN = "ILLEGAL_TERRAIN"
    NO_CONTACT = "NO_CONTACT"
    CAP_EXCEEDED = "CAP_EXCEEDED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNCITED_EVIDENCE = "UNCITED_EVIDENCE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TIMEOUT = "TIMEOUT"
    PARSE_FAILED = "PARSE_FAILED"


@unique
class Flag(StrEnum):
    """Something changed on the way in that is not a rejection."""

    TEXT_TRUNCATED = "TEXT_TRUNCATED"  # cut at its cap (ADR-0013 section 3)
