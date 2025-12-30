import argparse
import sys

from sound_viz.constants import ACTIVE_PLAYER_FILE, MSG_FILE


def output_string(args: argparse.Namespace, output: str) -> None:
    if args.output == "stdout":
        sys.stdout.write(f"\r{output}")
        sys.stdout.flush()
    elif args.output == "waybar":
        print(f"{output}", flush=True)


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


def get_active_player() -> str:
    return get_text_from_file(ACTIVE_PLAYER_FILE)


def set_active_player(player: str) -> None:
    write_to_file(player, ACTIVE_PLAYER_FILE)
