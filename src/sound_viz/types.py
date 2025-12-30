from typing import Literal, TypedDict


class RetryScan(Exception):
    """
    Raised when the device scan should be retried.
    """


SigAction = Literal["bare_animate", "scan_device"]


class GlobalState(TypedDict):
    """
    Global state of the application.
    """

    message: str | None
    anim_start: float
    animating: bool
    sig_action: SigAction | None
