# ncsb
## An ncurses Squeezebox controller for Logitech Media Server (LMS)

## Features

- slick curses TUI to control your squeezeboxes / squeezelite
- free-text and contextual search
- current playlist management
- player control
- album art in sixel-compliant terminals

## Installation

Requires python 3 (tested on 3.9), requests and hy

To install these with pip into your current environment (venv etc...),
```
$ pip install -r requirements.txt
```

## usage

with dependencies available to your environment,
```
$ python3 ncsb
```

## Todo

- finish album art (handle failed sixel import)
- file browser
- detailed track info
- standard packaging
- vim-style commands?
- colour themes
