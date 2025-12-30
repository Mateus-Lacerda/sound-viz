import glob
import os
import time
from typing import cast, get_args

from sound_viz.constants import ACTION_FILE, PID_DIR
from sound_viz.types import GlobalState, SigAction
from sound_viz.util import get_text_from_file


def signal_handler(signum: int, frame: object, global_state: GlobalState):
    """
    Called when SIGUSR1 is received. Reads the message and triggers animation.
    """
    try:
        text = get_text_from_file()
        action = get_text_from_file(ACTION_FILE) or "bare_animate"
        if action not in get_args(SigAction):
            action = "bare_animate"
        action = cast(SigAction, action)
        if text:
            global_state["message"] = text
            global_state["anim_start"] = time.time()
            global_state["sig_action"] = action
            global_state["animating"] = True
    except Exception:
        pass


def send_signal_to_all_processes(sig: int) -> None:
    if os.path.exists(PID_DIR):
        pid_files = glob.glob(os.path.join(PID_DIR, "*"))
        for p_file in pid_files:
            try:
                with open(p_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, sig)
            except Exception:
                try:
                    os.remove(p_file)
                except:  # noqa: E722
                    pass
