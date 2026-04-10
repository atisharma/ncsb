#!/usr/bin/env python3
"""ncsb — Command-line interface to Lyrion Music Server.

A unified CLI for controlling LMS players, searching the library,
and launching the ncurses TUI.

Usage:
    ncsb <command> [options]

Commands:
  TUI:
    tui <server>              Launch ncurses TUI

  Playback:
    play                      Start playback
    stop                      Stop playback
    pause                     Toggle pause
    next                      Skip to next track
    prev                      Go to previous track
    seek [+N|-N]              Seek forward/backward N seconds
    jump <pos>                Jump to playlist position

  Volume & Power:
    volume [N]                Set volume (0-100) or show current
    vol+ [N]                  Increase volume by N (default 5)
    vol- [N]                  Decrease volume by N (default 5)
    power [on|off]            Power on/off or show status

  Playlist:
    clear                     Clear playlist
    delete <pos>              Delete track at position
    move <from> <to>          Move track in playlist
    shuffle [0|1|2]           Set/query shuffle (off/songs/albums)
    repeat [0|1|2]            Set/query repeat (off/song/playlist)
    current                   Show current playlist with position marker

  Library:
    search <query>            Search library
    search-all <query>        Unified search across all types
    load <kind> <id>          Load album/artist/track
    songinfo <track_id>       Show detailed track info

  Status:
    info                      Show current track info
    playing                   Show playing status (one-line or JSON)
    status                    Show player status (JSON)
    players                   List available players
    serverstatus              Show server status (JSON)
    version                   Show LMS version

  Server:
    rescan                    Trigger library rescan
    rescan-progress           Show rescan progress

  Radio & Sleep:
    radio <url>               Play internet radio stream
    sleep [N]                 Set sleep timer N minutes, or query

Global options:
    -H, --host HOST           LMS server host
    -p, --port PORT           LMS server port
    -P, --player PLAYER       Player name
    -m, --mac MAC             Player MAC address

Config file:
    ~/.config/ncsb/config.toml
    
    host = "sol"
    player = "juno"
    port = 9000

Environment:
    LMS_HOST                  LMS server hostname
    LMS_PORT                  LMS server port
    NCSB_PLAYER               Default player name
"""
import sys
import os
import json
from pathlib import Path

import click

from ncsb import lms_controller as lms


# Config file handling
CONFIG_FILE = Path.home() / '.config' / 'ncsb' / 'config.toml'


def read_config():
    """Read config file and return defaults dict for click."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    
    try:
        with open(CONFIG_FILE, 'rb') as f:
            return tomllib.load(f)
    except Exception:
        return {}


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


def resolve_player(server, player_name=None, mac=None):
    """Resolve player name to MAC address."""
    if mac:
        return mac
    if not player_name:
        player_name = os.environ.get('NCSB_PLAYER', '')
    if not player_name:
        raise click.ClickException("Specify --player NAME or --mac MAC or set NCSB_PLAYER")
    players = lms.players(server)
    match = [p for p in players if p['name'].lower() == player_name.lower()]
    if not match:
        names = ', '.join(p['name'] for p in players)
        raise click.ClickException(f'Player "{player_name}" not found. Available: {names}')
    return match[0]['playerid']


# --- CLI group ---

@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-H', '--host', envvar='LMS_HOST', default='localhost', help='LMS server host')
@click.option('-p', '--port', envvar='LMS_PORT', default=9000, type=int, help='LMS server port')
@click.option('-P', '--player', envvar='NCSB_PLAYER', default=None, help='Player name')
@click.option('-m', '--mac', default=None, help='Player MAC address')
@click.pass_context
def cli(ctx, host, port, player, mac):
    """ncsb — Command-line interface to Lyrion Music Server."""
    ctx.ensure_object(dict)
    ctx.obj['host'] = host
    ctx.obj['port'] = port
    ctx.obj['player'] = player
    ctx.obj['mac'] = mac
    # Lazy server creation - only when needed
    ctx.obj['server'] = None


def get_server(ctx):
    """Get or create LMS server connection."""
    if ctx.obj['server'] is None:
        ctx.obj['server'] = lms.Server(ctx.obj['host'], ctx.obj['port'])
    return ctx.obj['server']


def get_mac(ctx):
    """Resolve player MAC address."""
    return resolve_player(get_server(ctx), ctx.obj['player'], ctx.obj['mac'])


# --- TUI command ---

@cli.command('tui')
@click.argument('server', required=False, default=None)
@click.option('--port', '-p', default=9000, help='Server port')
@click.pass_context
def cmd_tui(ctx, server, port):
    """Launch the ncurses TUI."""
    from ncsb.tui import main as tui_main
    host = server or ctx.obj['host']
    p = port or ctx.obj['port']
    tui_main(server_ip=host, port=p)


# --- Playback commands ---

@cli.command()
@click.pass_context
def play(ctx):
    """Start playback."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.play(server, mac)
    click.echo(f"Playing: {lms.title(server, mac)}")


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop playback."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.stop(server, mac)
    click.echo("Stopped")


@cli.command()
@click.pass_context
def pause(ctx):
    """Toggle pause."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.pause(server, mac)
    click.echo(f"Mode: {lms.mode(server, mac)}")


@cli.command()
@click.pass_context
def next(ctx):
    """Skip to next track."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_skip(server, mac)
    click.echo(f"Now playing: {lms.title(server, mac)}")


@cli.command()
@click.pass_context
def prev(ctx):
    """Go to previous track."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_prev(server, mac)
    click.echo(f"Now playing: {lms.title(server, mac)}")


@cli.command()
@click.argument('offset', required=False, default='+5')
@click.pass_context
def seek(ctx, offset):
    """Seek forward (+N), backward (-N), or to absolute seconds."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    if offset.startswith('+'):
        lms.seek_forward(server, mac)
        click.echo("Seeked forward 5s")
    elif offset.startswith('-'):
        lms.seek_backward(server, mac)
        click.echo("Seeked backward 5s")
    else:
        try:
            secs = int(offset)
            server.send([mac, ["time", str(secs)]])
            click.echo(f"Seeked to {secs}s")
        except ValueError:
            raise click.ClickException("Seek requires +N, -N, or absolute seconds")


@cli.command()
@click.argument('pos', type=int)
@click.pass_context
def jump(ctx, pos):
    """Jump to playlist position (0-indexed)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_jump(server, mac, pos)
    click.echo(f"Jumped to {pos}: {lms.title(server, mac)}")


# --- Volume & Power commands ---

@cli.command()
@click.argument('volume', required=False, default=None)
@click.pass_context
def volume(ctx, volume):
    """Set volume (0-100) or show current."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    if volume is not None:
        if volume.startswith('+') or volume.startswith('-'):
            lms.volume_change(server, mac, int(volume))
        else:
            lms.volume(server, mac, int(volume))
    st = lms.status(server, mac)
    click.echo(f"Volume: {st.get('mixer volume', '?')}")


@cli.command('vol+')
@click.argument('delta', type=int, required=False, default=5)
@click.pass_context
def vol_up(ctx, delta):
    """Increase volume by N (default 5)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.volume_change(server, mac, delta)
    st = lms.status(server, mac)
    click.echo(f"Volume: {st.get('mixer volume', '?')}")


@cli.command('vol-')
@click.argument('delta', type=int, required=False, default=5)
@click.pass_context
def vol_down(ctx, delta):
    """Decrease volume by N (default 5)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.volume_change(server, mac, -delta)
    st = lms.status(server, mac)
    click.echo(f"Volume: {st.get('mixer volume', '?')}")


@cli.command()
@click.argument('state', type=click.Choice(['on', 'off', 'toggle']), required=False, default=None)
@click.pass_context
def power(ctx, state):
    """Power on/off or show status."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    if state is None:
        st = lms.status(server, mac)
        power = st.get('power', '?')
        click.echo(f"Power: {'on' if power == '1' else 'off'}")
    elif state == 'on':
        lms.power(server, mac, 1)
        click.echo("Power: on")
    elif state == 'off':
        lms.power(server, mac, 0)
        click.echo("Power: off")
    elif state == 'toggle':
        lms.power(server, mac, 'toggle')
        st = lms.status(server, mac)
        power = st.get('power', '?')
        click.echo(f"Power: {'on' if power == '1' else 'off'}")


# --- Playlist commands ---

@cli.command()
@click.pass_context
def clear(ctx):
    """Clear playlist."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_clear(server, mac)
    click.echo("Playlist cleared")


@cli.command()
@click.argument('pos', type=int)
@click.pass_context
def delete(ctx, pos):
    """Delete track at position."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_delete(server, mac, pos)
    click.echo(f"Deleted track at position {pos}")


@cli.command()
@click.argument('from_pos', type=int)
@click.argument('to_pos', type=int)
@click.pass_context
def move(ctx, from_pos, to_pos):
    """Move track in playlist."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_move(server, mac, from_pos, to_pos)
    click.echo(f"Moved track {from_pos} to {to_pos}")


@cli.command()
@click.argument('mode', type=click.Choice(['0', '1', '2', 'off', 'songs', 'albums']), required=False, default=None)
@click.pass_context
def shuffle(ctx, mode):
    """Set/query shuffle (0/off, 1/songs, 2/albums)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    modes = {'0': 0, 'off': 0, '1': 1, 'songs': 1, '2': 2, 'albums': 2}
    names = {'0': 'off', '1': 'songs', '2': 'albums'}
    if mode is None:
        st = lms.status(server, mac)
        m = st.get('playlist shuffle', '?')
        click.echo(f"Shuffle: {names.get(str(m), m)}")
    else:
        val = modes[mode]
        lms.playlist_shuffle(server, mac, val)
        click.echo(f"Shuffle: {names[str(val)]}")


@cli.command()
@click.argument('mode', type=click.Choice(['0', '1', '2', 'off', 'song', 'playlist']), required=False, default=None)
@click.pass_context
def repeat(ctx, mode):
    """Set/query repeat (0/off, 1/song, 2/playlist)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    modes = {'0': 0, 'off': 0, '1': 1, 'song': 1, '2': 2, 'playlist': 2}
    names = {'0': 'off', '1': 'song', '2': 'playlist'}
    if mode is None:
        st = lms.status(server, mac)
        m = st.get('playlist repeat', '?')
        click.echo(f"Repeat: {names.get(str(m), m)}")
    else:
        val = modes[mode]
        lms.playlist_repeat(server, mac, val)
        click.echo(f"Repeat: {names[str(val)]}")


@cli.command()
@click.pass_context
def current(ctx):
    """Show current playlist with position marker."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    st = lms.status(server, mac)
    playlist = st.get('playlist_loop', [])
    current_idx = int(st.get('playlist_cur_index', -1))

    if not playlist:
        click.echo("Playlist is empty")
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

        click.echo(f"{marker} {idx:3d}. {title}{artist_str}{dur_str}")


# --- Library commands ---

@cli.command('search')
@click.argument('query', nargs=-1, required=True)
@click.option('--kind', type=click.Choice(['artists', 'albums', 'songs']), default='albums', help='Search type')
@click.pass_context
def cmd_search(ctx, query, kind):
    """Search the library."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    query_str = ' '.join(query)

    result = lms.search(server, mac, kind, query_str)
    loop_keys = {'albums': 'albums_loop', 'artists': 'artists_loop',
                 'songs': 'titles_loop'}
    loop_key = loop_keys.get(kind, f'{kind}_loop')
    items = result.get(loop_key, [])
    count = result.get('count', len(items))

    click.echo(f"Found {count} {kind}:")
    for item in items[:25]:
        if kind == 'albums':
            click.echo(f"  [{item.get('id', '?')}] {item.get('album', '?')}")
        elif kind == 'artists':
            click.echo(f"  [{item.get('id', '?')}] {item.get('artist', '?')}")
        elif kind == 'songs':
            title = item.get('title', '?')
            artist = item.get('artist', '')
            if artist:
                click.echo(f"  [{item.get('id', '?')}] {title} — {artist}")
            else:
                click.echo(f"  [{item.get('id', '?')}] {title}")


@cli.command('search-all')
@click.argument('query', nargs=-1, required=True)
@click.pass_context
def cmd_search_all(ctx, query):
    """Unified search across artists, albums, and tracks."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    query_str = ' '.join(query)
    total = 0

    # Search artists
    try:
        result = lms.search(server, mac, 'artists', query_str)
        items = result.get('artists_loop', [])
        if items:
            click.echo("\nArtists:")
            for item in items[:10]:
                total += 1
                click.echo(f"  [{item.get('id', '?')}] {item.get('artist', '?')}")
    except Exception:
        pass

    # Search albums
    try:
        result = lms.search(server, mac, 'albums', query_str)
        items = result.get('albums_loop', [])
        if items:
            click.echo("\nAlbums:")
            for item in items[:10]:
                total += 1
                click.echo(f"  [{item.get('id', '?')}] {item.get('album', '?')}")
    except Exception:
        pass

    # Search tracks
    try:
        result = lms.search(server, mac, 'songs', query_str)
        items = result.get('titles_loop', [])
        if items:
            click.echo("\nTracks:")
            for item in items[:10]:
                total += 1
                title = item.get('title', '?')
                artist = item.get('artist', '')
                if artist:
                    click.echo(f"  [{item.get('id', '?')}] {title} — {artist}")
                else:
                    click.echo(f"  [{item.get('id', '?')}] {title}")
    except Exception:
        pass

    if total == 0:
        click.echo("No results found")
    else:
        click.echo(f"\nTotal: {total} results")


@cli.command()
@click.argument('kind', type=click.Choice(['album', 'artist', 'track']))
@click.argument('item_id', type=int)
@click.option('--action', type=click.Choice(['load', 'add', 'insert']), default='load', help='Playlist action')
@click.pass_context
def load(ctx, kind, item_id, action):
    """Load album/artist/track into playlist."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    lms.playlist_control(server, mac, item_id, action=action, kind=kind)
    click.echo(f"Loaded {kind} {item_id} (action={action})")


@cli.command()
@click.argument('track_id', type=int)
@click.pass_context
def songinfo(ctx, track_id):
    """Show detailed track info."""
    server = get_server(ctx)
    info = lms.songinfo(server, track_id)
    if info:
        loop = info.get('songinfo_loop', [])
        if loop:
            for item in loop:
                for key, value in item.items():
                    click.echo(f"{key:20s}: {value}")
        else:
            click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"No info found for track {track_id}")


# --- Status commands ---

@cli.command()
@click.pass_context
def info(ctx):
    """Show current track info."""
    server = get_server(ctx)
    mac = get_mac(ctx)

    st = lms.status(server, mac)
    shuffle = st.get('playlist shuffle', '?')
    repeat = st.get('playlist repeat', '?')
    shuffle_modes = {'0': 'off', '1': 'songs', '2': 'albums'}
    repeat_modes = {'0': 'off', '1': 'song', '2': 'playlist'}

    click.echo(f"Title:    {lms.title(server, mac)}")
    click.echo(f"Artist:   {lms.artist(server, mac)}")
    click.echo(f"Album:    {lms.album(server, mac)}")
    click.echo(f"Mode:     {lms.mode(server, mac)}")
    click.echo(f"Time:     {_fmt_time(lms.track_elapsed(server, mac))}/{_fmt_time(lms.track_duration(server, mac))}")
    click.echo(f"Volume:   {st.get('mixer volume', '?')}")
    click.echo(f"Track:    {int(st.get('playlist_cur_index', 0))+1}/{st.get('playlist_tracks', '?')}")
    click.echo(f"Shuffle:  {shuffle_modes.get(str(shuffle), shuffle)}")
    click.echo(f"Repeat:   {repeat_modes.get(str(repeat), repeat)}")


@cli.command()
@click.argument('server', required=False, default=None)
@click.argument('mac', required=False, default=None)
@click.option('--json', '-j', 'json_output', is_flag=True, help='Output as JSON')
@click.pass_context
def playing(ctx, server, mac, json_output):
    """Show playing status (one-line or JSON)."""
    s = get_server(ctx)
    m = get_mac(ctx) if mac is None else mac

    mode = lms.mode(s, m)
    title = lms.title(s, m)
    album = lms.album(s, m)
    artist = lms.artist(s, m)
    duration = lms.track_duration(s, m)
    remaining = lms.track_remaining(s, m)
    elapsed = lms.track_elapsed(s, m)
    elapsed_fraction = lms.track_elapsed_fraction(s, m)

    if json_output:
        click.echo(json.dumps({
            "mode": mode,
            "title": title,
            "album": album,
            "artist": artist,
            "duration": duration,
            "remaining": remaining,
            "elapsed": elapsed,
            "elapsed_fraction": elapsed_fraction
        }, indent=2))
    else:
        if mode == "play":
            click.echo(f"⏵ {album} / {title} - {elapsed_fraction:.0%}")
        elif mode == "stop":
            click.echo("⏹")
        elif mode == "pause":
            click.echo("⏸")


@cli.command()
@click.pass_context
def status(ctx):
    """Show player status (JSON)."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    st = lms.status(server, mac)
    click.echo(json.dumps(st, indent=2))


@cli.command()
@click.pass_context
def players(ctx):
    """List available players."""
    server = get_server(ctx)
    players = lms.players(server)
    click.echo(f"{'Name':<12} {'MAC':<20} {'Conn':<6} {'Play':<6} {'Pwr':<6} {'Model':<15}")
    click.echo("-" * 70)
    for p in players:
        click.echo(f"{p['name']:<12} {p['playerid']:<20} {str(p.get('connected', '?')):<6} "
                   f"{str(p.get('isplaying', '?')):<6} {str(p.get('power', '?')):<6} "
                   f"{p.get('model', '?'):<15}")


@cli.command()
@click.pass_context
def serverstatus(ctx):
    """Show server status (JSON)."""
    server = get_server(ctx)
    st = lms.serverstatus(server)
    click.echo(json.dumps(st, indent=2))


@cli.command()
@click.pass_context
def version(ctx):
    """Show LMS version."""
    server = get_server(ctx)
    v = lms.version(server)
    click.echo(f"LMS version: {v}")


# --- Server commands ---

@cli.command()
@click.pass_context
def rescan(ctx):
    """Trigger library rescan."""
    server = get_server(ctx)
    lms.rescan(server)
    click.echo("Library rescan triggered")


@cli.command('rescan-progress')
@click.pass_context
def rescan_progress(ctx):
    """Show rescan progress."""
    server = get_server(ctx)
    progress = lms.rescan_progress(server)
    if progress:
        click.echo(f"Rescan in progress: {progress}")
    else:
        click.echo("No rescan in progress")


@cli.command()
@click.pass_context
def config(ctx):
    """Show config file location and current settings."""
    click.echo(f"Config file: {CONFIG_FILE}")
    if CONFIG_FILE.exists():
        click.echo("\nCurrent config:")
        cfg = read_config()
        for key, value in sorted(cfg.items()):
            click.echo(f"  {key}: {value}")
        click.echo("\nEffective settings (config + env + CLI):")
        click.echo(f"  host: {ctx.obj['host']}")
        click.echo(f"  port: {ctx.obj['port']}")
        click.echo(f"  player: {ctx.obj['player'] or '(not set)'}")
        click.echo(f"  mac: {ctx.obj['mac'] or '(not set)'}")
    else:
        click.echo("\nNo config file found.")
        click.echo("\nCreate one at ~/.config/ncsb/config.toml:")
        click.echo('  [default]')
        click.echo('  host = "sol"')
        click.echo('  player = "juno"')
        click.echo('  port = 9000')


# --- Radio & Sleep commands ---

@cli.command()
@click.argument('url')
@click.option('--title', '-t', default=None, help='Station name')
@click.option('--add', 'add_mode', is_flag=True, help='Add to playlist instead of playing')
@click.pass_context
def radio(ctx, url, title, add_mode):
    """Play internet radio stream."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    if add_mode:
        lms.add_url(server, mac, url, title)
        click.echo(f"Added radio stream: {title or url}")
    else:
        lms.play_url(server, mac, url, title)
        lms.play(server, mac)
        click.echo(f"Now playing: {title or url}")


@cli.command()
@click.argument('minutes', type=int, required=False, default=None)
@click.pass_context
def sleep(ctx, minutes):
    """Set sleep timer N minutes, or query remaining."""
    server = get_server(ctx)
    mac = get_mac(ctx)
    if minutes is not None:
        seconds = minutes * 60
        lms.sleep(server, mac, seconds)
        click.echo(f"Sleep timer set: {minutes} minutes")
    else:
        remaining = lms.sleep(server, mac, '?')
        if remaining:
            mins = int(float(remaining)) / 60
            click.echo(f"Sleep timer: {mins:.1f} minutes remaining")
        else:
            click.echo("Sleep timer: not set")


def main():
    """Entry point for ncsb CLI."""
    config_defaults = read_config()
    cli(default_map=config_defaults)


if __name__ == '__main__':
    main()
