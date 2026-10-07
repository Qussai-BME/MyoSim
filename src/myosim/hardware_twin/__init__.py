"""Deterministic software-only actuator twin for MyoSim research experiments.

This module models a command/actuator layer; it is not a hardware driver or a
validated model of any specific physical prosthesis.
"""

from myosim.hardware_twin.backend import (
    ActuatorProfile,
    FaultKind,
    FaultWindow,
    HardwareTwinBackend,
    HardwareTwinSnapshot,
    HardwareTwinStats,
    HardwareTwinTraceSample,
    default_hand_profiles,
    load_hand_profiles,
    trace_to_dict,
)

__all__ = [
    "ActuatorProfile",
    "FaultKind",
    "FaultWindow",
    "HardwareTwinBackend",
    "HardwareTwinSnapshot",
    "HardwareTwinStats",
    "HardwareTwinTraceSample",
    "default_hand_profiles",
    "load_hand_profiles",
    "trace_to_dict",
]
