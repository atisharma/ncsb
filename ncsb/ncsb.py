import hy
import sys
import argparse
import json

from ncsb.main import main
import ncsb.lms_controller as lms


def cli():
    parser = argparse.ArgumentParser(description="An ncurses squeezebox controller for the Logitech Media Server (LMS)")
    parser.add_argument("server", type=str, help="IP address or network name of server")
    parser.add_argument("--port", "-p", type=int, default=9000, help="server port (usually 9000)")
    args = parser.parse_args()
    main(server_ip=args.server, port=args.port)

def playing():
    parser = argparse.ArgumentParser(description="An ncurses squeezebox controller for the Logitech Media Server (LMS)")
    parser.add_argument("server", type=str, help="IP address or network name of server")
    parser.add_argument("mac", type=str, help="mac address of player (playerid)")
    parser.add_argument("--port", "-p", type=int, default=9000, help="server port (usually 9000)")
    parser.add_argument("--json", "-j", action="store_true", help="output json")
    args = parser.parse_args()
    with lms.Server(args.server, args.port) as server:
        mode = lms.mode(server, args.mac)
        title = lms.title(server, args.mac)
        album = lms.album(server, args.mac)
        artist = lms.artist(server, args.mac)
        duration = lms.track_duration(server, args.mac)
        remaining = lms.track_remaining(server, args.mac)
        elapsed = lms.track_elapsed(server, args.mac)
        elapsed_fraction = lms.track_elapsed_fraction(server, args.mac)
        if args.json:
            print(json.dumps(
                {
                    "mode": mode,
                    "title": title,
                    "album": album,
                    "artist": artist,
                    "duration": duration,
                    "remaining": remaining,
                    "elapsed": elapsed,
                    "elapsed_fraction": elapsed_fraction
                },
                indent=4))
        else:
            if mode == "play":
                print(f"⏵ {album} / {title} {elapsed_fraction:.0%}")
            elif mode == "stop":
                printf("⏹")
            elif mode == "pause":
                printf("⏸")
                
                    

