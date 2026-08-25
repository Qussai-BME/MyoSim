"""Domain-specific errors used to preserve intelligible failure boundaries."""


class MyoSimError(Exception):
    """Base error for expected MyoSim domain failures."""


class ConfigurationError(MyoSimError):
    """Raised when an explicit configuration cannot satisfy V1 invariants."""


class IntentValidationError(MyoSimError):
    """Raised when an external intent record cannot satisfy the public contract."""


class BackendError(MyoSimError):
    """Raised when a physics backend cannot load, step, or restore a valid state."""


class SafetyViolation(MyoSimError):
    """Raised when a control target violates a configured safety boundary."""


class TaskError(MyoSimError):
    """Raised when a simulation task is malformed or cannot progress."""
