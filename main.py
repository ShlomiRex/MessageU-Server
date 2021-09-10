from Server.ProtocolDefenitions import FILE_PORT
from Server.Server import Server


def read_port():
    with open(FILE_PORT) as file:
        port = int(file.readline())
    return port


if __name__ == '__main__':
    port = read_port()
    server = Server(port)
    server.start()
