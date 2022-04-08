import hy
import sys

from main import main

def cli():
    if len(sys.argv) == 2:
        cmd, ip = sys.argv
        port = 9000
    else:
        cmd, ip, port = sys.argv
    main(server_ip=ip, port=port)
