import argparse
import glob
import os
import signal
import subprocess
import sys
import time
from typing import Any, Literal, TypedDict, cast, get_args

import numpy as np
import soundcard as sc

PID_DIR = "/tmp/sound_viz_pids"
MSG_FILE = "/tmp/sound_viz.msg"
ACTION_FILE = "/tmp/sound_viz.action"


THEMES = {
    "blocks": "  ▂▃▄▅▆▇█",
    "braille": "⠀⢀⣀⣠⣤⣴⣾⣿",
    "lines": " _-¯‾",
}


class RetryScan(Exception):
    pass


SigAction = Literal["bare_animate", "scan_device"]


class GlobalState(TypedDict):
    message: str | None
    anim_start: float
    animating: bool
    sig_action: SigAction | None


global_state = GlobalState(
    {
        "message": None,
        "anim_start": 0,
        "animating": False,
        "sig_action": None,
    }
)


def write_to_file(text: str, file: str = MSG_FILE) -> None:
    try:
        with open(file, "w") as f:
            f.write(text)
    except IOError:
        pass


def get_text_from_file(file: str = MSG_FILE) -> str:
    try:
        with open(file, "r") as f:
            return f.read().strip()
    except IOError:
        return ""


def signal_handler(signum, frame):
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


def output_string(args: argparse.Namespace, output: str) -> None:
    if args.output == "stdout":
        sys.stdout.write(f"\r{output}")
        sys.stdout.flush()
    elif args.output == "waybar":
        print(f"{output}", flush=True)


def animate_message(
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


def run_playerctl_controller(args: argparse.Namespace) -> None:
    """
    CONTROLLER MODE (Broadcast):
    1. Executes playerctl.
    2. Ensures we get the NEW status (waits for change).
    3. Sends signal to ALL processes.
    """
    command = args.playerctl_command
    output = "DONE"

    try:
        if command == "play-pause":
            old_status = (
                subprocess.run(
                    ["playerctl", "-p", "spotify", "status"],
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
                .lower()
            )

            subprocess.run(["playerctl", "-p", "spotify", "play-pause"])

            new_status = old_status
            for _ in range(10):
                time.sleep(0.05)
                new_status = (
                    subprocess.run(
                        ["playerctl", "-p", "spotify", "status"],
                        capture_output=True,
                        text=True,
                    )
                    .stdout.strip()
                    .lower()
                )

                if new_status != old_status and new_status != "":
                    break

            output = new_status.upper() if new_status else "..."

        else:
            result = subprocess.run(
                ["playerctl", "-p", "spotify", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            raw_out = result.stdout.decode("utf-8").strip()

            if command == "next":
                output = "󰒭 NEXT"
            elif command == "previous":
                output = "󰒮 PREV"
            elif raw_out:
                output = raw_out

        output = output[:25]

    except Exception:
        output = "ERR"

    write_to_file(output)

    send_signal_to_all_processes(signal.SIGUSR1)

    sys.exit(0)


def find_active_device(args: argparse.Namespace, mics: list):
    frames = [".", "o", "O", "(O)", "( )", " "]

    monitors = [m for m in mics if "Monitor" in m.name] * 3
    if not monitors:
        return mics[0]

    for i, mic in enumerate(monitors):
        viz = frames[i % len(frames)].center(args.width)
        output_string(args, viz)

        try:
            with mic.recorder(samplerate=44100, blocksize=1024) as recorder:
                data = recorder.record(numframes=1024)
                vol = np.max(np.abs(data))
                if vol > 0.005:
                    if args.output == "stdout":
                        sys.stdout.write("\033[2K\r")
                    elif args.output == "waybar":
                        print(" ", flush=True)
                    return mic
        except Exception:
            continue

    if args.output == "stdout":
        sys.stdout.write("\033[2K\r")
    elif args.output == "waybar":
        print(" ", flush=True)
    return None


def get_mic(
    args: argparse.Namespace,
    my_pid_file: str,
):
    try:
        mics = sc.all_microphones(include_loopback=True)
        if args.list:
            for i, mic in enumerate(mics):
                print(f"{i:2} : {mic.name}")

            os.remove(my_pid_file)
            return None

        if args.device is not None:
            mic = mics[args.device]
        else:
            mic = find_active_device(args, mics)
            if mic is None:
                mic = next((m for m in mics if "Monitor" in m.name), mics[0])
    except Exception as e:
        if args.verbose:
            print(f"Erro: {e}")
        if os.path.exists(my_pid_file):
            os.remove(my_pid_file)
        return None

    return mic


def play_loop(
    args: argparse.Namespace,
    mic: Any,
):
    bar_chars = THEMES[args.theme]
    blocksize = 128
    try:
        with mic.recorder(samplerate=44100, blocksize=blocksize) as recorder:
            while True:
                if global_state["animating"]:
                    animation_finished = animate_message(args, recorder)
                    if not animation_finished:
                        continue

                if global_state["sig_action"] == "scan_device":
                    raise RetryScan

                data = recorder.record(numframes=blocksize)
                mono = data[:, 0]
                step = max(1, len(mono) // args.width)
                resampled = mono[::step][: args.width]

                output = ""
                for val in resampled:
                    val = val * args.gain
                    if args.mode == "wave":
                        level = (val + 1) / 2
                    else:
                        level = abs(val)

                    if level > 1.0:
                        level = 1.0
                    if level < 0.0:
                        level = 0.0

                    idx = int(level * (len(bar_chars) - 1))
                    output += bar_chars[idx]

                output_string(args, output)

    except KeyboardInterrupt:
        if args.output == "stdout":
            sys.stdout.write("\033[2K\r")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="A lightweight sound visualization tool."
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all available audio input devices.",
    )
    parser.add_argument(
        "-d",
        "--device",
        type=int,
        default=None,
        help="Index of the audio device to use. If not provided, it will try to find an active monitor.",
    )
    parser.add_argument(
        "-t",
        "--theme",
        type=str,
        choices=THEMES.keys(),
        default="blocks",
        help="Visualization theme (blocks, braille, lines).",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=16,
        help="Width of the visualization in characters.",
    )
    parser.add_argument(
        "-g",
        "--gain",
        type=float,
        default=6.0,
        help="Input gain factor to amplify the signal.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["wave", "abs"],
        default="wave",
        help="Visualization mode: 'wave' for waveform, 'abs' for absolute values.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="stdout",
        help="Output destination: 'stdout' (default) or 'waybar'.",
    )
    parser.add_argument(
        "-p",
        "--playerctl-command",
        type=str,
        choices=["play-pause", "next", "previous"],
        help="Control a media player using playerctl (play-pause, next, previous).",
    )
    parser.add_argument(
        "-sd",
        "--scan-device",
        action="store_true",
        help="Switch to the next available audio device.",
    )

    args = parser.parse_args()

    if args.playerctl_command:
        run_playerctl_controller(args)
        return

    if args.scan_device:
        write_to_file("󱉶 Device")
        write_to_file("scan_device", ACTION_FILE)
        send_signal_to_all_processes(signal.SIGUSR1)
        return

    os.makedirs(PID_DIR, exist_ok=True)

    my_pid = os.getpid()
    my_pid_file = os.path.join(PID_DIR, str(my_pid))

    with open(my_pid_file, "w") as f:
        f.write(str(my_pid))

    signal.signal(signal.SIGUSR1, signal_handler)

    if not (mic := get_mic(args, my_pid_file)):
        return

    try:
        while True:
            try:
                play_loop(args, mic)
            except RetryScan:
                new_mic = get_mic(args, my_pid_file)
                if new_mic is not None:
                    mic = new_mic
                write_to_file("", ACTION_FILE)
                global_state["sig_action"] = None
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if args.verbose:
            print(f"Erro inesperado: {e}")
    finally:
        if os.path.exists(my_pid_file):
            os.remove(my_pid_file)


if __name__ == "__main__":
    main()
