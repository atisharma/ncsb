import hy
import sys
import argparse

from ncsb.main import main


def cli():
    parser = argparse.ArgumentParser(description="An ncurses squeezebox controller for the Logitech Media Server (LMS)")
    parser.add_argument("server", type=str)
    parser.add_argument("--port", "-p", type=int, default=9000)
    args = parser.parse_args()
    main(server_ip=args.server, port=args.port)
