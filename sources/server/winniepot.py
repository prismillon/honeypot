import os
import time
import socket
import datetime


if os.geteuid() != 0:
    print("Please run this script as sudo.")
    quit()

_ip = "0.0.0.0"
_port = 13000

TIMEOUT = 15
LOGFILE = ""

KEEP_SNAPSHOTS = True
STOCKAGE_SERVER = ("", 5566)

session = {
        "connected": False,
        "ip": "0"
}

_custom_functions = {}
_functions_name = ("on_connection", "on_connection_lost", "on_ping", "on_foreign_ping", "on_command", "on_restart")

_server = socket.socket()
try:
    _server.bind((_ip, _port))
except OSError as e:
    print("[ERROR] - The port that the server is using is currently inavailable, please wait a few minutes before restarting.")
    quit()

_server.settimeout(TIMEOUT)
_server.listen()


def _use_custom_function(name, *args):
    if not (name in _custom_functions):
        return

    try:
        _custom_functions[name](*args)
    except TypeError as e:
        print(e)
        print(f"[ERROR] - Event \"{name}\" takes {len(args)} arguments, please check your script before running again.")
        _server.close()
        stop()
        quit()


def _get_date():
    date = datetime.datetime.now()
    return date.strftime("%m-%d_%Hh%M")


def _serve_forever():
    ping_counter = 0
    while True:
        try:
            client, clientinfo = _server.accept()
            message = client.recv(1024).decode("utf-8")
            if not session["connected"]:
                log_console("someone just logged in.")
                session["connected"] = True
                _use_custom_function("on_connection")
        except socket.timeout:
            if not session["connected"]:
                # no signal from honeypot, but no one is connected.
                continue

            log_console("no signal from honeypot, stopping it.")
            restart_procedure()
            session["connected"] = False

            _use_custom_function("on_connection_lost")
            continue
        except Exception as e:
            print(e)


        if ping_counter >= 60:
            log_console("honeypot has been up for too long (10m), restarting it.")
            restart_procedure()
            session["connected"] = False
            ping_counter = 0
            continue

        if message == "1":
            ping_counter += 1
            _use_custom_function("on_ping")
            continue

        if not message.startswith("<honey>"):
            log_console(f"({clientinfo[0]}) foreign data: {message}", "WARNING")
            _use_custom_function("on_foreign_ping", message)
            continue

        try:
            ip, *message = message[7:].split("=")
            session["ip"] = ip.split(" ")[0]
            message = '='.join(message)
        except:
            log_console("Bad format.")
            log_console(message)
            continue

        _use_custom_function("on_command", message)
        log_console(message, session["ip"])
        log_to_file(message, session["ip"])


def custom_event(event: str):
    if event not in _functions_name:
        raise ValueError(f"{event} not in {_functions_name}.")

    def wrapper(func):
        _custom_functions[event] = func
        return func
    return wrapper


def restart_procedure():
    _use_custom_function("on_restart")

    stop_honeypot()

    snapshot = ""
    if KEEP_SNAPSHOTS:
        log_console("extracting and sending current state to the distant stockage server.")
        snapshot = take_snapshot()

    if LOGFILE != '' or snapshot:
        tar_name = tar_files(LOGFILE, snapshot)
        if STOCKAGE_SERVER[0]:
            try:
                if os.stat(LOGFILE).st_size > 0:
                    try:
                        send_file(tar_name)
                    except Exception as e:
                        log_console("Could not send the summary to the server. Error:")
                        print(e)
            except FileNotFoundError:
                return

            try:
                os.remove(LOGFILE)
            except FileNotFoundError:
                pass
            os.remove(tar_name)

    if snapshot:
        remove_snapshot(snapshot)


    log_console("restarting the honeypot.")
    restore_honeypot()
    start_honeypot()
    log_console("honeypot restarted.")


def send_file(filename):
    HOST = STOCKAGE_SERVER
    BUFFER =8192
    FLAG = "<INFO>"
    FILE_START, FILE_END = "<START_OF_FILE>", "<END_OF_FILE>"

    if not os.path.exists(filename):
        log_console(f"{filename} doesn't exist, can't send it to the stockage server.", "WARNING")
        return

    server = socket.socket()
    server.connect(HOST)

    log_console("Sending the file", "INFO")
    server.send(f"{FLAG}{filename}{FLAG}{FILE_START}".encode("utf-8"))
    with open(filename, "rb") as file:
        while data := file.read(BUFFER):
            server.send(data)
        server.send(FILE_END.encode("utf-8"))

    log_console(f"Sent {filename} to the server", "INFO")
    server.close()


def stop_honeypot():
    os.system("lxc stop --force honey")


def take_snapshot() -> str:
    snapname = f"snap{_get_date()}"
    os.system(f"lxc snapshot honey {snapname}")
    return snapname

def remove_snapshot(name):
    os.system(f"lxc delete honey/{name}")


def restore_honeypot(original="template"):
    os.system(f"lxc restore honey {original}")


def start_honeypot():
    os.system("lxc start honey")


def stop():
    _server.close()
    log_console("Stopping honeypot...")
    stop_honeypot()
    log_console("Restoring honeypot...")
    restore_honeypot()
    log_console("Done.")
    quit()


def tar_files(logfile, snapshot):
    name = f"{_get_date()}.tar"
    os.system(f"tar -cazf {name} {logfile} -C /var/snap/lxd/common/lxd/snapshots/honey/{snapshot}/rootfs .")
    return name


def log_console(message, logtype="INFO"):
    print(f"<{_get_date()}> [{logtype}] - {message}")

def log_to_file(message, logtype="INFO"):
    if not LOGFILE:
        return

    with open(LOGFILE, "a") as file:
        file.write(f"<{_get_date()}> [{logtype}] - {message}\n")


def run():
    try:
        log_console("starting honeypot...")
        start_honeypot()
        log_console("started.")
        _serve_forever()
    except KeyboardInterrupt:
        print("Exiting...")

    stop()