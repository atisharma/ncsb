# ncsb - An ncurses Squeezebox controller for Logitech Media Server (LMS)


## Features

- slick curses TUI to control your squeezeboxes / squeezelite
- full-featured CLI for scripting and remote control
- free-text and contextual search
- current playlist management
- player control
- album art in sixel-compliant terminals (experimental, off by default)


## Installation

Requires Python 3.9+, with packages: hy, hyrule, requests, click.

```
$ pip install -e .
```

Or install from PyPI:
```
$ pip install ncsb
```

For optional cover art in terminal, also install libsixel-python and a sixel-supporting terminal (see below).


## Usage

### CLI

The unified `ncsb` command provides both TUI and CLI access:

```
$ ncsb -H lms-server players
$ ncsb -H lms-server -P juno info
$ ncsb -H lms-server search miles --kind artists
```

**Global options:**
- `-H, --host` — LMS server host (default: $LMS_HOST or localhost)
- `-p, --port` — LMS server port (default: $LMS_PORT or 9000)
- `-P, --player` — Player name (default: $NCSB_PLAYER)
- `-m, --mac` — Player MAC address

**Commands:**

| Command | Description |
|---------|-------------|
| `tui` | Launch ncurses TUI |
| `play`, `stop`, `pause` | Playback control |
| `next`, `prev`, `seek`, `jump` | Track navigation |
| `volume`, `vol+`, `vol-` | Volume control |
| `power` | Power on/off |
| `current` | Show playlist |
| `shuffle`, `repeat` | Playlist modes |
| `search`, `search-all` | Library search |
| `load` | Load album/artist/track |
| `info`, `playing`, `status` | Status display |
| `players`, `serverstatus`, `version` | Server info |
| `config` | Show config file and settings |
| `radio`, `sleep` | Radio and sleep timer |

Per-command help: `ncsb search --help`

### TUI

```
$ ncsb tui lms-server
```

In any screen, press `?` for available commands.


## Environment Variables

| Variable | Description |
|----------|-------------|
| `LMS_HOST` | Default LMS server hostname |
| `LMS_PORT` | Default LMS server port |
| `NCSB_PLAYER` | Default player name |


## Config File

Create `~/.config/ncsb/config.toml`:

```toml
host = "sol"
player = "juno"
port = 9000
```

**Precedence** (highest to lowest):
1. CLI arguments
2. Environment variables
3. Config file
4. Built-in defaults

Show current config: `ncsb config`


## Examples

```bash
# List players
ncsb -H sol players

# Show current track
ncsb -H sol -P juno info

# Search and play
ncsb -H sol -P juno search kind of blue --kind albums
ncsb -H sol -P juno load album 6468

# Volume control
ncsb -H sol -P juno volume 75
ncsb -H sol -P juno vol+ 5

# Play radio stream
ncsb -H sol -P juno radio https://stream.example.com/mp3 --title "Jazz FM"

# Set sleep timer
ncsb -H sol -P juno sleep 30

# JSON output for scripting
ncsb -H sol -P juno playing --json
```


## Sixel Terminal Support

Incomplete list of sixel-supporting terminals [here](https://github.com/saitoha/libsixel#terminal-requirements)
See also [foot](https://codeberg.org/dnkl/foot),
patched gnome-terminal?,
xterm launched with `xterm -ti vt340`
or with `xterm*decTerminalID : vt340` in `.Xresources`.

If you are seeing boxes or junk instead of nice unicode symbols for play/pause etc, you need to use a font with more complete unicode support. Hack works well.

In-terminal coverart requires libsixel to be installed on your system (presumably via your package manager) and a sixel-supporting terminal. Cover art notifications require libnotify to be installed.


## Bugs

- flashing when loading album art, due to working around the nasty interactions between curses and sixel
- unable to write to top left of screen with curses when sixel image is displayed
- album title text update can partially overwrite the cover art sixel image
- because the font size and resolution is not known to curses, the album art size cannot be scaled to a terminal-appropriate size


## Credits

Copyright A S Sharma (2021), released under the GPL v3.0 (see LICENSE and AUTHORS).
Thanks also to elParaguayo (LMSTools), Ralph Irving (squeezelite) and the Slimerver / Logitech Media Server authors for inspiration.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/atisharma/ncsb)
