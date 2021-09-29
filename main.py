import logging

from Server.ProtocolDefenitions import FILE_PORT
from Server.Server import Server

logger = logging.getLogger(__name__)


def read_port():
    logger.debug(f"Reading from '{FILE_PORT}'...")
    with open(FILE_PORT) as file:
        res = int(file.readline())
        logger.debug("OK")
        return res


if __name__ == '__main__':
    port = read_port()
    server = Server(port)
    server.start()
