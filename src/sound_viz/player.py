import argparse
import os
import signal
import subprocess
import sys
import time

import numpy as np
import soundcard as sc

from sound_viz.ipc import send_signal_to_all_processes
from sound_viz.util import output_string, write_to_file, get_active_player
from sound_viz.types import GlobalState


def run_playerctl_controller(args: argparse.Namespace, global_state: GlobalState) -> None:
    """
    CONTROLLER MODE (Broadcast):
    1. Executes playerctl.
    2. Ensures we get the NEW status (waits for change).
    3. Sends signal to ALL processes.
    """
    command = args.playerctl_command
    output = "DONE"

    try:
        player = get_active_player() or "spotify"
        if command == "play-pause":
            old_status = (
                subprocess.run(
                    ["playerctl", "-p", player, "status"],
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
                .lower()
            )

            subprocess.run(["playerctl", "-p", player, "play-pause"])

            new_status = old_status
            for _ in range(10):
                time.sleep(0.05)
                new_status = (
                    subprocess.run(
                        ["playerctl", "-p", player, "status"],
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
                ["playerctl", "-p", player, command],
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


def get_available_players() -> list:
    try:
        players = (
            subprocess.run(
                ["playerctl", "-l"],
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .split("\n")
        )
        players = list(map(lambda x: x.split(".")[0], players))
    except Exception:
        players = []

    return players
