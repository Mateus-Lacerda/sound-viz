# Sound Viz

A simple sound visualization tool designed for Linux. It works great in the terminal and is specifically tailored for integration with **Waybar**.

## Demo

https://github.com/user-attachments/assets/bcf4a20e-59e4-46c0-8023-e6fd69194222


## Features
- Some themes: Blocks, Braille, Lines
- Two visualization modes: Waveform (from -1 to 1, rests in the middle), Absolute Values (from 0 to 1, rests at the bottom)
- Output: Standard Output, Waybar
- Media Player Control: Play/Pause, Next, Previous (with animations)
- Autodetection: If no device is specified, it will try to find an active audio monitor and use it
- Broadcast: Actions are received and broadcasted to all instances of the program with IPC
- Players: Switch between the players controllable by `playerctl`

## Dependencies

- `uv` (for installation)
- `playerctl` (optional, for media player control)
- `waybar` (optional, to make it truly beautiful)

## Installation

Clone the repository and install using `uv`:

```bash
git clone https://github.com/Mateus-Lacerda/sound-viz.git
cd sound-viz
uv tool install .
```

This will make `sound_viz` available in your `PATH`.
To know where the executable was installed, run:

```bash
which sound_viz
# Example output: /home/your-user/.local/bin
```

## CLI:

```console
$ sound_viz --help

usage: sound_viz [-h] [-l] [-d DEVICE] [-t {blocks,braille,lines}]
                 [-w WIDTH] [-g GAIN] [-m {wave,abs}] [-v] [-o OUTPUT]
                 [-p {play-pause,next,previous}] [-sd]
                 [-lp {chromium,firefox,spotify}] [-sp] [-ip]

A lightweight sound visualization tool.

options:
  -h, --help            show this help message and exit
  -l, --list            List all available audio input devices.
  -d DEVICE, --device DEVICE
                        Index of the audio device to use. If not provided,
                        it will try to find an active monitor.
  -t {blocks,braille,lines}, --theme {blocks,braille,lines}
                        Visualization theme (blocks, braille, lines).
  -w WIDTH, --width WIDTH
                        Width of the visualization in characters.
  -g GAIN, --gain GAIN  Input gain factor to amplify the signal.
  -m {wave,abs}, --mode {wave,abs}
                        Visualization mode: 'wave' for waveform, 'abs' for
                        absolute values.
  -v, --verbose         Enable verbose output for debugging.
  -o OUTPUT, --output OUTPUT
                        Output destination: 'stdout' (default) or 'waybar'.
  -p {play-pause,next,previous}, --playerctl-command {play-pause,next,previous}
                        Control a media player using playerctl (play-pause,
                        next, previous).
  -sd, --scan-device    Switch to the next available audio device.
  -lp {chromium,firefox,spotify}, --list-player {chromium,firefox,spotify}
                        Media player to control (default: spotify).
  -sp, --switch-player  Switch to the next available media player.
  -ip, --icon-player    Output the icon of the active media player.
```

## Usage with Waybar

To add the visualizer to your Waybar, add the following configuration to your `config` file (usually located at `~/.config/waybar/config`).

> [!NOTE]
> Ensure the path in `"exec"`, `"on-click"`, etc., points to the **absolute** path where `sound_viz` was installed (e.g., `/home/user/.local/bin/sound_viz` or your specific user path).

```json
    "custom/sound_viz": {
        "exec": "/path/to/executable/sound_viz --output waybar",
        "tail": true,
        "format": "{}",
        "on-click": "/path/to/executable/sound_viz --playerctl-command play-pause",
        "on-scroll-up": "/path/to/executable/sound_viz --playerctl-command previous",
        "on-scroll-down": "/path/to/executable/sound_viz --playerctl-command next",
        "on-click-middle": "/path/to/executable/sound_viz --scan-device"
    },
    "custom/sound_viz_player": {
        "exec": "/path/to/executable/sound_viz --output waybar --icon-player",
        "tail": true,
        "format": "{}",
        "on-click": "/path/to/executable/sound_viz --switch-player",
    }
```
