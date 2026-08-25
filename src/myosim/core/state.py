"""Canonical controller state vocabulary.

State-machine implementation lives in `myosim.control`; this module gives
upper layers a stable import path without creating a reverse dependency.
"""

from myosim.core.types import ControllerState

__all__ = ["ControllerState"]
