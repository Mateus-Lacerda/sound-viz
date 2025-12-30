import argparse
import os
import signal
import sys
from functools import partial
from time import sleep
from typing import Any

from sound_viz.ascii_anim import animate_message
from sound_viz.constants import ACTION_FILE, PID_DIR, PLAYER_ICONS, THEMES
from sound_viz.ipc import send_signal_to_all_processes, signal_handler
from sound_viz.player import get_available_players, get_mic, run_playerctl_controller
from sound_viz.types import GlobalState, RetryScan
from sound_viz.util import output_string, write_to_file, get_active_player, set_active_player

global_state = GlobalState(
    {
        "message": None,
        "anim_start": 0,
        "animating": False,
        "sig_action": None,
    }
)


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
                    animation_finished = animate_message(global_state, args, recorder)
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

                if args.verbose:
                    output += f"\n{global_state}"

                output_string(args, output)

    except KeyboardInterrupt:
        if args.output == "stdout":
            sys.stdout.write("\033[2K\r")
        raise


def ouput_player_icon(args: argparse.Namespace):
    while True:
        active_player = get_active_player()
        icon = PLAYER_ICONS.get(active_player, "")
        output_string(args, icon)
        sleep(0.5)


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
    parser.add_argument(
        "-lp",
        "--list-player",
        type=str,
        choices=get_available_players(),
        default="spotify",
        help="Media player to control (default: spotify).",
    )
    parser.add_argument(
        "-sp",
        "--switch-player",
        action="store_true",
        help="Switch to the next available media player.",
    )
    parser.add_argument(
        "-ip",
        "--icon-player",
        action="store_true",
        help="Output the icon of the active media player.",
    )

    args = parser.parse_args()

    if args.playerctl_command:
        run_playerctl_controller(args, global_state)
        return

    if args.scan_device:
        write_to_file("󱉶 Device")
        write_to_file("scan_device", ACTION_FILE)
        send_signal_to_all_processes(signal.SIGUSR1)
        return

    if args.switch_player:
        write_to_file(" Player")
        write_to_file("bare_animate", ACTION_FILE)
        active_player = get_active_player() or "spotify"
        all_players = get_available_players()
        try:
            current_player_idx = all_players.index(active_player)
        except ValueError:
            current_player_idx = 0
        next_player = all_players[
            (current_player_idx + 1) % len(all_players)
        ]
        set_active_player(next_player)
        return

    os.makedirs(PID_DIR, exist_ok=True)

    my_pid = os.getpid()
    my_pid_file = os.path.join(PID_DIR, str(my_pid))

    with open(my_pid_file, "w") as f:
        f.write(str(my_pid))

    handler = partial(signal_handler, global_state=global_state)
    signal.signal(signal.SIGUSR1, handler)

    if args.icon_player:
        ouput_player_icon(args)
        return

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
