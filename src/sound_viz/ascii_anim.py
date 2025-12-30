import argparse
import time
from typing import Any

from sound_viz.util import output_string
from sound_viz.types import GlobalState


def animate_message(
    global_state: GlobalState,
    args: argparse.Namespace,
    recorder: Any,
    message: str | None = None,
) -> bool:
    """
    Animates the message by revealing it character by character.
    """
    elapsed = time.time() - global_state["anim_start"]
    msg = message or global_state["message"] or ""

    if elapsed < 2.0:
        num_chars = int(elapsed * 15) + 1
        if num_chars > len(msg):
            num_chars = len(msg)

        display_text = msg[:num_chars].center(args.width)

        if int(elapsed * 4) % 2 == 0:
            display_text = f"[{display_text.strip()}]".center(args.width)

        output_string(args, display_text)
        time.sleep(0.05)
        return False
    else:
        global_state["animating"] = False
        global_state["message"] = None
        recorder.flush()
        return True
