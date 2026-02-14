#!/usr/bin/env python3
"""ncsb CLI — Agent-friendly command-line interface to Lyrion Music Server.

Usage:
    ncsb_cli.py <command> [options]

Commands:
    play        Start playback
    stop        Stop playback
    pause       Toggle pause
    next        Skip to next track
    prev        Go to previous track
    volume      Set or show volume (0-100)
    info        Show current track info
    jump        Jump to playlist position (0-indexed)
    clear       Clear playlist
    search      Search the music library
    load        Load album/artist/track by ID
    players     List available players
    status      Show player status

Global options:
    --player NAME   Player name (case-insensitive)
    --mac MAC       Player MAC address directly
    --host HOST     LMS server host (default: $LMS_HOST or sol.lan.letterbox.pw)
    --port PORT     LMS server port (default: $LMS_PORT or 9000)

Environment:
    NCSB_PLAYER     Default player name
    LMS_HOST        LMS server hostname
    LMS_PORT        LMS server port
"""

import sys
import os
import json

# Add ncsb to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ncsb import lms_controller as lms


def get_server():
    host = os.environ.get('LMS_HOST', 'sol.lan.letterbox.pw')
    port = int(os.environ.get('LMS_PORT', '9000'))
    return lms.Server(host, port)


def resolve_player(server, player_name=None, mac=None):
    """Resolve player name to MAC address."""
    if mac:
        return mac
    if not player_name:
        player_name = os.environ.get('NCSB_PLAYER', '')
    if not player_name:
        print("Error: specify --player NAME or --mac MAC or set NCSB_PLAYER", file=sys.stderr)
        sys.exit(1)
    players = lms.players(server)
    match = [p for p in players if p['name'].lower() == player_name.lower()]
    if not match:
        names = ', '.join(p['name'] for p in players)
        print(f'Error: player "{player_name}" not found. Available: {names}', file=sys.stderr)
        sys.exit(1)
    return match[0]['playerid']


def parse_global_args(args):
    """Parse global args, return (player_name, mac, host, port, remaining_args)."""
    player = None
    mac = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == '--player' and i + 1 < len(args):
            player = args[i + 1]; i += 2
        elif args[i] == '--mac' and i + 1 < len(args):
            mac = args[i + 1]; i += 2
        elif args[i] == '--host' and i + 1 < len(args):
            os.environ['LMS_HOST'] = args[i + 1]; i += 2
        elif args[i] == '--port' and i + 1 < len(args):
            os.environ['LMS_PORT'] = args[i + 1]; i += 2
        else:
            remaining.append(args[i]); i += 1
    return player, mac, remaining


def cmd_play(server, mac, args):
    lms.play(server, mac)
    info = lms.title(server, mac)
    print(f"Playing: {info}")


def cmd_stop(server, mac, args):
    lms.stop(server, mac)
    print("Stopped")


def cmd_pause(server, mac, args):
    lms.pause(server, mac)
    m = lms.mode(server, mac)
    print(f"Mode: {m}")


def cmd_next(server, mac, args):
    lms.playlist_skip(server, mac)
    info = lms.title(server, mac)
    print(f"Now playing: {info}")


def cmd_prev(server, mac, args):
    lms.playlist_prev(server, mac)
    info = lms.title(server, mac)
    print(f"Now playing: {info}")


def cmd_volume(server, mac, args):
    if args:
        vol = args[0]
        if vol.startswith('+') or vol.startswith('-'):
            lms.volume_change(server, mac, int(vol))
        else:
            lms.volume(server, mac, int(vol))
    st = lms.status(server, mac)
    print(f"Volume: {st.get('mixer volume', '?')}")


def cmd_info(server, mac, args):
    t = lms.title(server, mac)
    a = lms.artist(server, mac)
    al = lms.album(server, mac)
    elapsed = lms.track_elapsed(server, mac)
    duration = lms.track_duration(server, mac)
    m = lms.mode(server, mac)
    st = lms.status(server, mac)
    vol = st.get('mixer volume', '?')
    idx = st.get('playlist_cur_index', '?')
    total = st.get('playlist_tracks', '?')

    print(f"Title:    {t}")
    print(f"Artist:   {a}")
    print(f"Album:    {al}")
    print(f"Mode:     {m}")
    print(f"Time:     {_fmt_time(elapsed)}/{_fmt_time(duration)}")
    print(f"Volume:   {vol}")
    print(f"Track:    {int(idx)+1 if idx != '?' else '?'}/{total}")


def cmd_jump(server, mac, args):
    if not args:
        print("Usage: ncsb_cli.py jump <position>", file=sys.stderr)
        sys.exit(1)
    pos = int(args[0])
    lms.playlist_jump(server, mac, pos)
    info = lms.title(server, mac)
    print(f"Jumped to {pos}: {info}")


def cmd_clear(server, mac, args):
    lms.playlist_clear(server, mac)
    print("Playlist cleared")


def cmd_search(server, mac, args):
    if not args:
        print("Usage: ncsb_cli.py search [--kind albums|artists|songs] <query>", file=sys.stderr)
        sys.exit(1)

    kind = 'albums'
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] == '--kind' and i + 1 < len(args):
            kind = args[i + 1]; i += 2
        else:
            query_parts.append(args[i]); i += 1
    query = ' '.join(query_parts)

    result = lms.search(server, mac, kind, query)
    loop_key = f'{kind}_loop'
    items = result.get(loop_key, [])
    count = result.get('count', len(items))
    print(f"Found {count} {kind}:")
    for item in items[:25]:
        if kind == 'albums':
            print(f"  [{item.get('id', '?')}] {item.get('album', '?')}")
        elif kind == 'artists':
            print(f"  [{item.get('id', '?')}] {item.get('artist', '?')}")
        elif kind == 'songs' or kind == 'titles':
            print(f"  [{item.get('id', '?')}] {item.get('title', '?')}")
        else:
            print(f"  {item}")


def cmd_load(server, mac, args):
    if len(args) < 2:
        print("Usage: ncsb_cli.py load <album|artist|track> <id> [--action load|add|insert]", file=sys.stderr)
        sys.exit(1)
    kind = args[0]
    item_id = int(args[1])
    action = 'load'
    if '--action' in args:
        idx = args.index('--action')
        if idx + 1 < len(args):
            action = args[idx + 1]
    lms.playlist_control(server, mac, item_id, action=action, kind=kind)
    print(f"Loaded {kind} {item_id} (action={action})")


def cmd_players(server, mac_unused, args):
    players = lms.players(server)
    fmt = "{:<12s} {:<20s} connected={} playing={} power={}"
    for p in players:
        print(fmt.format(
            p['name'], p['playerid'],
            p.get('connected', '?'), p.get('isplaying', '?'), p.get('power', '?')
        ))


def cmd_status(server, mac, args):
    st = lms.status(server, mac)
    print(json.dumps(st, indent=2))


def _fmt_time(seconds):
    if seconds is None or seconds == '?':
        return '?:??'
    s = int(float(seconds))
    return f"{s // 60}:{s % 60:02d}"


COMMANDS = {
    'play': cmd_play,
    'stop': cmd_stop,
    'pause': cmd_pause,
    'next': cmd_next,
    'prev': cmd_prev,
    'volume': cmd_volume,
    'info': cmd_info,
    'jump': cmd_jump,
    'clear': cmd_clear,
    'search': cmd_search,
    'load': cmd_load,
    'players': cmd_players,
    'status': cmd_status,
}

PLAYER_OPTIONAL = {'players'}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)

    command = args[0]
    args = args[1:]

    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        sys.exit(1)

    player, mac, remaining = parse_global_args(args)
    server = get_server()

    if command in PLAYER_OPTIONAL:
        COMMANDS[command](server, None, remaining)
    else:
        resolved_mac = resolve_player(server, player, mac)
        COMMANDS[command](server, resolved_mac, remaining)


if __name__ == '__main__':
    main()
