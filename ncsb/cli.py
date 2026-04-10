#!/usr/bin/env python3
"""ncsb-cli — Agent-friendly command-line interface to Lyrion Music Server.

Usage:
    ncsb-cli <command> [options]

Commands:
  Playback:
    play            Start playback
    stop            Stop playback
    pause           Toggle pause
    next            Skip to next track
    prev            Go to previous track
    seek [+N|-N]    Seek forward/backward N seconds (default ±5)
    jump <pos>      Jump to playlist position (0-indexed)

  Volume & Power:
    volume [N]      Set volume (0-100) or show current
    vol+ [N]        Increase volume by N (default 5)
    vol- [N]        Decrease volume by N (default 5)
    power [on|off]  Power on/off or show status

  Playlist:
    clear           Clear playlist
    delete <pos>    Delete track at position
    move <from> <to> Move track in playlist
    shuffle [0|1|2] Set/query shuffle (off/songs/albums)
    repeat [0|1|2]  Set/query repeat (off/song/playlist)
    current         Show current playlist with position marker

  Library:
    search [--kind K] <query>  Search library (artists/albums/songs)
    search-all <query>         Unified search across all types
    load <kind> <id> [--action A]  Load album/artist/track
    songinfo <track_id>        Show detailed track info

  Server:
    players         List available players
    status          Show player status (JSON)
    serverstatus    Show server status (JSON)
    version         Show LMS version
    rescan          Trigger library rescan
    rescan-progress Show rescan progress
    info            Show current track info

  Radio & Sleep:
    radio <url> [--title T] [--add]  Play/add internet radio
    sleep [N]        Set sleep timer N minutes, or query remaining

Global options:
    --player NAME   Player name (case-insensitive)
    --mac MAC       Player MAC address directly
    --host HOST     LMS server host (default: $LMS_HOST or localhost)
    --port PORT     LMS server port (default: $LMS_PORT or 9000)

Environment:
    NCSB_PLAYER     Default player name
    LMS_HOST        LMS server hostname (default: localhost)
    LMS_PORT        LMS server port (default: 9000)
"""
import sys
import os
import json

from ncsb import lms_controller as lms


def get_server():
    host = os.environ.get('LMS_HOST', 'localhost')
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
    """Parse global args, return (player_name, mac, remaining_args)."""
    player = None
    mac = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == '--player' and i + 1 < len(args):
            player = args[i + 1]
            i += 2
        elif args[i] == '--mac' and i + 1 < len(args):
            mac = args[i + 1]
            i += 2
        elif args[i] == '--host' and i + 1 < len(args):
            os.environ['LMS_HOST'] = args[i + 1]
            i += 2
        elif args[i] == '--port' and i + 1 < len(args):
            os.environ['LMS_PORT'] = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return player, mac, remaining


def _fmt_time(seconds):
    """Format seconds as M:SS."""
    if seconds is None or seconds == '?':
        return '?:??'
    try:
        s = int(float(seconds))
        return f"{s // 60}:{s % 60:02d}"
    except (ValueError, TypeError):
        return '?:??'


def _fmt_duration(seconds):
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds is None:
        return '?'
    try:
        s = int(float(seconds))
        if s >= 3600:
            return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        return f"{s // 60}:{s % 60:02d}"
    except (ValueError, TypeError):
        return '?'


# --- Playback commands ---

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


def cmd_seek(server, mac, args):
    if not args:
        args = ['+5']
    offset = args[0]
    if offset.startswith('+'):
        lms.seek_forward(server, mac)
        print(f"Seeked forward 5s")
    elif offset.startswith('-'):
        lms.seek_backward(server, mac)
        print(f"Seeked backward 5s")
    else:
        # Absolute seek
        try:
            secs = int(offset)
            # LMS uses "time <secs>" for absolute position
            lms.Server.send(server, [mac, ["time", str(secs)]])
            print(f"Seeked to {secs}s")
        except ValueError:
            print("Error: seek requires +N, -N, or absolute seconds", file=sys.stderr)
            sys.exit(1)


def cmd_jump(server, mac, args):
    if not args:
        print("Usage: ncsb-cli jump <position>", file=sys.stderr)
        sys.exit(1)
    pos = int(args[0])
    lms.playlist_jump(server, mac, pos)
    info = lms.title(server, mac)
    print(f"Jumped to {pos}: {info}")


# --- Volume & Power commands ---

def cmd_volume(server, mac, args):
    if args:
        vol = args[0]
        if vol.startswith('+') or vol.startswith('-'):
            lms.volume_change(server, mac, int(vol))
        else:
            lms.volume(server, mac, int(vol))
    st = lms.status(server, mac)
    print(f"Volume: {st.get('mixer volume', '?')}")


def cmd_vol_up(server, mac, args):
    delta = int(args[0]) if args else 5
    lms.volume_change(server, mac, delta)
    st = lms.status(server, mac)
    print(f"Volume: {st.get('mixer volume', '?')}")


def cmd_vol_down(server, mac, args):
    delta = int(args[0]) if args else 5
    lms.volume_change(server, mac, -delta)
    st = lms.status(server, mac)
    print(f"Volume: {st.get('mixer volume', '?')}")


def cmd_power(server, mac, args):
    if not args:
        # Query current power state
        st = lms.status(server, mac)
        power = st.get('power', '?')
        print(f"Power: {'on' if power == '1' else 'off'}")
    elif args[0] == 'on':
        lms.power(server, mac, 1)
        print("Power: on")
    elif args[0] == 'off':
        lms.power(server, mac, 0)
        print("Power: off")
    elif args[0] == 'toggle':
        lms.power(server, mac, 'toggle')
        st = lms.status(server, mac)
        power = st.get('power', '?')
        print(f"Power: {'on' if power == '1' else 'off'}")
    else:
        print("Usage: ncsb-cli power [on|off|toggle]", file=sys.stderr)
        sys.exit(1)


# --- Playlist commands ---

def cmd_clear(server, mac, args):
    lms.playlist_clear(server, mac)
    print("Playlist cleared")


def cmd_delete(server, mac, args):
    if not args:
        print("Usage: ncsb-cli delete <position>", file=sys.stderr)
        sys.exit(1)
    pos = int(args[0])
    lms.playlist_delete(server, mac, pos)
    print(f"Deleted track at position {pos}")


def cmd_move(server, mac, args):
    if len(args) < 2:
        print("Usage: ncsb-cli move <from> <to>", file=sys.stderr)
        sys.exit(1)
    from_pos = int(args[0])
    to_pos = int(args[1])
    lms.playlist_move(server, mac, from_pos, to_pos)
    print(f"Moved track {from_pos} to {to_pos}")


def cmd_shuffle(server, mac, args):
    if not args:
        # Query current shuffle mode
        st = lms.status(server, mac)
        mode = st.get('playlist shuffle', '?')
        modes = {'0': 'off', '1': 'songs', '2': 'albums'}
        print(f"Shuffle: {modes.get(str(mode), mode)}")
    else:
        val = args[0]
        if val in ('0', 'off'):
            lms.playlist_shuffle(server, mac, 0)
            print("Shuffle: off")
        elif val in ('1', 'songs'):
            lms.playlist_shuffle(server, mac, 1)
            print("Shuffle: songs")
        elif val in ('2', 'albums'):
            lms.playlist_shuffle(server, mac, 2)
            print("Shuffle: albums")
        else:
            print("Usage: ncsb-cli shuffle [0|off|1|songs|2|albums]", file=sys.stderr)
            sys.exit(1)


def cmd_repeat(server, mac, args):
    if not args:
        # Query current repeat mode
        st = lms.status(server, mac)
        mode = st.get('playlist repeat', '?')
        modes = {'0': 'off', '1': 'song', '2': 'playlist'}
        print(f"Repeat: {modes.get(str(mode), mode)}")
    else:
        val = args[0]
        if val in ('0', 'off'):
            lms.playlist_repeat(server, mac, 0)
            print("Repeat: off")
        elif val in ('1', 'song'):
            lms.playlist_repeat(server, mac, 1)
            print("Repeat: song")
        elif val in ('2', 'playlist'):
            lms.playlist_repeat(server, mac, 2)
            print("Repeat: playlist")
        else:
            print("Usage: ncsb-cli repeat [0|off|1|song|2|playlist]", file=sys.stderr)
            sys.exit(1)


def cmd_current(server, mac, args):
    """Show current playlist with position marker."""
    st = lms.status(server, mac)
    playlist = st.get('playlist_loop', [])
    current_idx = int(st.get('playlist_cur_index', -1))
    mode = st.get('mode', '?')

    if not playlist:
        print("Playlist is empty")
        return

    for track in playlist:
        idx = int(track.get('playlist index', 0))
        title = track.get('title', '?')
        artist = track.get('artist', '')
        duration = track.get('duration')

        marker = '▶' if idx == current_idx else ' '
        dur_str = _fmt_duration(duration) if duration else ''
        artist_str = f" — {artist}" if artist else ''
        dur_str = f" [{dur_str}]" if dur_str else ''

        print(f"{marker} {idx:3d}. {title}{artist_str}{dur_str}")


# --- Library commands ---

def cmd_search(server, mac, args):
    if not args:
        print("Usage: ncsb-cli search [--kind albums|artists|songs] <query>", file=sys.stderr)
        sys.exit(1)

    kind = 'albums'
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] == '--kind' and i + 1 < len(args):
            kind = args[i + 1]
            i += 2
        else:
            query_parts.append(args[i])
            i += 1
    query = ' '.join(query_parts)

    result = lms.search(server, mac, kind, query)
    # Map kind to loop key
    loop_keys = {'albums': 'albums_loop', 'artists': 'artists_loop',
                 'songs': 'titles_loop', 'titles': 'titles_loop'}
    loop_key = loop_keys.get(kind, f'{kind}_loop')
    items = result.get(loop_key, [])
    count = result.get('count', len(items))
    print(f"Found {count} {kind}:")
    for item in items[:25]:
        if kind == 'albums':
            print(f"  [{item.get('id', '?')}] {item.get('album', '?')}")
        elif kind == 'artists':
            print(f"  [{item.get('id', '?')}] {item.get('artist', '?')}")
        elif kind in ('songs', 'titles'):
            title = item.get('title', '?')
            artist = item.get('artist', '')
            print(f"  [{item.get('id', '?')}] {title} — {artist}" if artist else f"  [{item.get('id', '?')}] {title}")
        else:
            print(f"  {item}")


def cmd_search_all(server, mac, args):
    """Unified search across artists, albums, and tracks."""
    if not args:
        print("Usage: ncsb-cli search-all <query>", file=sys.stderr)
        sys.exit(1)

    query = ' '.join(args)
    total = 0

    # Search artists
    try:
        result = lms.search(server, mac, 'artists', query)
        items = result.get('artists_loop', [])
        if items:
            print("\nArtists:")
            for item in items[:10]:
                total += 1
                print(f"  [{item.get('id', '?')}] {item.get('artist', '?')}")
    except Exception:
        pass

    # Search albums
    try:
        result = lms.search(server, mac, 'albums', query)
        items = result.get('albums_loop', [])
        if items:
            print("\nAlbums:")
            for item in items[:10]:
                total += 1
                print(f"  [{item.get('id', '?')}] {item.get('album', '?')}")
    except Exception:
        pass

    # Search tracks
    try:
        result = lms.search(server, mac, 'songs', query)
        items = result.get('titles_loop', [])
        if items:
            print("\nTracks:")
            for item in items[:10]:
                total += 1
                title = item.get('title', '?')
                artist = item.get('artist', '')
                print(f"  [{item.get('id', '?')}] {title} — {artist}" if artist else f"  [{item.get('id', '?')}] {title}")
    except Exception:
        pass

    if total == 0:
        print("No results found")
    else:
        print(f"\nTotal: {total} results")


def cmd_load(server, mac, args):
    if len(args) < 2:
        print("Usage: ncsb-cli load <album|artist|track> <id> [--action load|add|insert]", file=sys.stderr)
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


def cmd_songinfo(server, mac, args):
    if not args:
        print("Usage: ncsb-cli songinfo <track_id>", file=sys.stderr)
        sys.exit(1)
    track_id = args[0]
    info = lms.songinfo(server, track_id)
    if info:
        # Pretty print the song info
        loop = info.get('songinfo_loop', [])
        if loop:
            for item in loop:
                for key, value in item.items():
                    print(f"{key:20s}: {value}")
        else:
            print(json.dumps(info, indent=2))
    else:
        print(f"No info found for track {track_id}")


# --- Server commands ---

def cmd_players(server, mac_unused, args):
    players = lms.players(server)
    print(f"{'Name':<12} {'MAC':<20} {'Conn':<6} {'Play':<6} {'Pwr':<6} {'Model':<15}")
    print("-" * 70)
    for p in players:
        print(f"{p['name']:<12} {p['playerid']:<20} {str(p.get('connected', '?')):<6} "
              f"{str(p.get('isplaying', '?')):<6} {str(p.get('power', '?')):<6} "
              f"{p.get('model', '?'):<15}")


def cmd_status(server, mac, args):
    st = lms.status(server, mac)
    print(json.dumps(st, indent=2))


def cmd_serverstatus(server, mac_unused, args):
    st = lms.serverstatus(server)
    print(json.dumps(st, indent=2))


def cmd_version(server, mac_unused, args):
    v = lms.version(server)
    print(f"LMS version: {v}")


def cmd_rescan(server, mac_unused, args):
    lms.rescan(server)
    print("Library rescan triggered")


def cmd_rescan_progress(server, mac_unused, args):
    progress = lms.rescan_progress(server)
    if progress:
        print(f"Rescan in progress: {progress}")
    else:
        print("No rescan in progress")


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
    shuffle = st.get('playlist shuffle', '?')
    repeat = st.get('playlist repeat', '?')

    shuffle_modes = {'0': 'off', '1': 'songs', '2': 'albums'}
    repeat_modes = {'0': 'off', '1': 'song', '2': 'playlist'}

    print(f"Title:    {t}")
    print(f"Artist:   {a}")
    print(f"Album:    {al}")
    print(f"Mode:     {m}")
    print(f"Time:     {_fmt_time(elapsed)}/{_fmt_time(duration)}")
    print(f"Volume:   {vol}")
    print(f"Track:    {int(idx)+1 if idx != '?' else '?'}/{total}")
    print(f"Shuffle:  {shuffle_modes.get(str(shuffle), shuffle)}")
    print(f"Repeat:   {repeat_modes.get(str(repeat), repeat)}")


# --- Radio & Sleep commands ---

def cmd_radio(server, mac, args):
    if not args:
        print("Usage: ncsb-cli radio <url> [--title 'Station Name'] [--add]", file=sys.stderr)
        sys.exit(1)
    url = args[0]
    title = None
    add_mode = False
    i = 1
    while i < len(args):
        if args[i] == '--title' and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == '--add':
            add_mode = True
            i += 1
        else:
            i += 1
    if add_mode:
        lms.add_url(server, mac, url, title)
        print(f"Added radio stream: {title or url}")
    else:
        lms.play_url(server, mac, url, title)
        lms.play(server, mac)
        print(f"Now playing: {title or url}")


def cmd_sleep(server, mac, args):
    if args:
        try:
            minutes = int(args[0])
            seconds = minutes * 60
            lms.sleep(server, mac, seconds)
            print(f"Sleep timer set: {minutes} minutes")
        except ValueError:
            print("Error: minutes must be a number", file=sys.stderr)
            sys.exit(1)
    else:
        remaining = lms.sleep(server, mac, '?')
        if remaining:
            minutes = int(float(remaining)) / 60
            print(f"Sleep timer: {minutes:.1f} minutes remaining")
        else:
            print("Sleep timer: not set")


# --- Command registry ---

COMMANDS = {
    # Playback
    'play': cmd_play,
    'stop': cmd_stop,
    'pause': cmd_pause,
    'next': cmd_next,
    'prev': cmd_prev,
    'seek': cmd_seek,
    'jump': cmd_jump,
    # Volume & Power
    'volume': cmd_volume,
    'vol+': cmd_vol_up,
    'vol-': cmd_vol_down,
    'power': cmd_power,
    # Playlist
    'clear': cmd_clear,
    'delete': cmd_delete,
    'move': cmd_move,
    'shuffle': cmd_shuffle,
    'repeat': cmd_repeat,
    'current': cmd_current,
    # Library
    'search': cmd_search,
    'search-all': cmd_search_all,
    'load': cmd_load,
    'songinfo': cmd_songinfo,
    # Server
    'players': cmd_players,
    'status': cmd_status,
    'serverstatus': cmd_serverstatus,
    'version': cmd_version,
    'rescan': cmd_rescan,
    'rescan-progress': cmd_rescan_progress,
    'info': cmd_info,
    # Radio & Sleep
    'radio': cmd_radio,
    'sleep': cmd_sleep,
}

# Commands that don't require a player
PLAYER_OPTIONAL = {'players', 'serverstatus', 'version', 'rescan', 'rescan-progress', 'songinfo'}


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
