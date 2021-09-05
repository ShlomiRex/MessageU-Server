from src.database.Database import Database
from src.server.Server import Server


def read_port():
    with open("port.info") as file:
        port = int(file.readline())
    return port


if __name__ == '__main__':
    port = read_port()
    server = Server(port)
    server.start()

