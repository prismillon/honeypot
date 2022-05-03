# On the honeypot, this file is: /usr/bin/serve
#!/bin/python3
import sys
import os
import socket

HOST = ("IP_SERVER", 13000)

try:
    server = socket.socket()
    server.connect(HOST)
except:
    sys.exit(0)

args = sys.argv[1:]
if not args:
    sys.exit(0)

command = f"<honey>{'IP'}={' '.join(args)}"

try:
    server.send(command.encode("utf-8"))
    server.close()
except:
    pass