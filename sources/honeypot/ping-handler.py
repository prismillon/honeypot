# On the honeypot, this file is: /usr/bin/NetworkManager
#!/bin/python3.9
import socket
import time

HOST = ("IP", 13000)


def looping():
    first = True
    while True:
        try:
            server =  socket.socket()
            server.connect(HOST)
            if first:
                server.send("ip".encode("utf-8"))
                server.close()
                first = False
                continue
        except:
            continue
        server.send("1".encode("utf-8"))
        server.close()
        time.sleep(10)

try:
    import os
    if os.path.exists("/usr/bin/NetworkManager"):
        os.remove("/usr/bin/NetworkManager")
        looping()
except:
    pass