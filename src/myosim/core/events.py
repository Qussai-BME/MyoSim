"""Audit event contracts.

The V1 controller emits `StateTransition` values rather than mutating hidden
state. Experiment and reporting layers consume these records without importing
control internals.
"""

from myosim.core.types import StateTransition

__all__ = ["StateTransition"]
