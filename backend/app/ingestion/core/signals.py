from enum import Enum
from typing import Literal


class Signal(Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    SHUTDOWN = "shutdown"


# Desired state for a job, computed from last signal
DesiredState = Literal["idle", "running", "paused", "canceled", "shutdown"]
