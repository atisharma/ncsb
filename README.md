# ncsb - An ncurses Squeezebox controller for Logitech Media Server (LMS)


## Features

- slick curses TUI to control your squeezeboxes / squeezelite
- free-text and contextual search
- current playlist management
- player control
- album art in sixel-compliant terminals (experimental, off by default)
- regular crashes


## Screenshot / screencast

### players

![players screen](screenshots/players.png)
![playlist screen](screenshots/playlist.png)
![another playlist screen](screenshots/playlist-2.png)
![search screen](screenshots/search.png)
![search results screen](screenshots/search_results.png)

## Usage

with dependencies available to your environment,
```
$ ncsb lms-server
```
where `lms-server` is the hostname or IP address of your LMS server.

To use a port other than the default 9000, use the `--port` or `-p` optional argument,
```
$ ncsb -p 9090 lms-server
```

In any screen, press `?` for available commands.


## Installation

Requires python 3 (tested on 3.9-12), with python packages requests, hy (>=1.0) and (for optional coverart) libsixel-python.

To install these with pip into your current environment (venv etc...),
```
$ pip install -r requirements.txt
```

Incomplete list of sixel-supporting terminals [here](https://github.com/saitoha/libsixel#terminal-requirements)
See also [foot](https://codeberg.org/dnkl/foot),
patched gnome-terminal?,
xterm launced with `xterm -ti vt340`
or with `xterm*decTerminalID : vt340` in `.Xresources`.


If you are seeing boxes or junk instead of nice unicode symbols for play/pause etc, you need to use a font with more complete unicode support.
Hack works well.

In-terminal coverart requires libsixel to be installed on your system (presumably via your package manager) and a sixel-supporting terminal. Cover art notifications require libnotify to be installed.


## Bugs

- flashing when loading album art, due to working around the nasty interactions between curses and sixel
- unable to write to top left of screen with curses when sixel image is displayed
- album title text update can partially overwrite the cover art sixel image
- because the font size and resolution is not known to curses, the album art size cannot be scaled to a terminal-appropriate size


## Todo

- play general URL (pasted in)
- apps / podcast / menu
- detailed track info
- vim-style commands?
- colour themes
- use events instead of polling
- fix screencast
- scrolling when text is too wide for terminal


## Credits

Copyright A S Sharma (2021), released under the GPL v3.0 (see LICENSE and AUTHORS).
Thanks also to elParaguayo (LMSTools), Ralph Irving (squeezelite) and the Slimerver / Logitech Media Server authors for inspiration.
