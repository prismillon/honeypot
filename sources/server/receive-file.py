import os
import socket


HOST = ("0.0.0.0", 5566)
BUFFER = 4096
FLAG = b"<INFO>"
FILE_START, FILE_END = b"<START_OF_FILE>", b"<END_OF_FILE>"

server = socket.socket()
server.bind(HOST)
server.listen()


def valid_packet(message: bytes) -> bool:
    return message.startswith(FLAG)

def serve_forever(server: socket.socket):
    while True:
        client, clientinfo = server.accept()

        message = client.recv(BUFFER)
        if not valid_packet(message):
            client.close()
            continue

        data = message.split(FLAG)
        filename = data[1]
        try:
            filename = filename.decode("utf-8")
        except UnicodeDecodeError:
            print("Filename is in weird format. Aborting download.")
            client.close()
            continue

        content = data[2][len(FILE_START):]
        with open(filename, 'wb') as target_file:
            while not content.endswith(FILE_END):
                target_file.write(content)
                content = client.recv(BUFFER)
            content = content[:-len(FILE_END)]
            target_file.write(content)
        
        print(f"[INFO] - New {filename} file downloaded !")
        client.close()


try:
    serve_forever(server)
except KeyboardInterrupt:
    print("Exiting the server...")
finally:
    server.close()
