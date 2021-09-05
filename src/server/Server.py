import select
import socket
import selectors
import logging

from src.database.Database import Database

RECV_BUFF_S = 1024      # Amount of bytes to read at once from socket.

logger = logging.getLogger("server")
sel = selectors.DefaultSelector()

class Server:
    def __init__(self, port: int, ip: str = "127.0.0.1", max_clients_queue: int = 5):
        """
        Creates the server that listens to multiple clients. To start run the 'start' function.
        :param port: Port to bind to
        :param ip: Ip to bind to
        :param max_clients_queue: Maximum concurrent users in queue (if over, server refuses to server new user)
        """
        self.version = 1
        self.port = port
        self.ip = ip

        server_sock = socket.socket()
        server_sock.bind((self.ip, self.port))
        server_sock.listen(max_clients_queue)
        server_sock.setblocking(False)

        self.inputs = [server_sock]     # Read from sockets
        self.server_sock = server_sock
        self.outputs = []               # Write to sockets

        self.database = Database()

    def start(self):
        """
        Starts the server.
        :return:
        """
        logger.info(f"Server is listening on: {self.ip}:{self.port}")
        while self.inputs:
            readable, writeable, exceptions = select.select(self.inputs, [], [])
            for sock in readable:
                if sock is self.server_sock:
                    client, address = self.server_sock.accept()
                    self.inputs.append(client)
                    logger.info(f"New client connection from: {address}")
                    self.__greet(client)
                    self.__notify_all(f"Client {address} has joined the chat\n", [self.server_sock, client])
                else:
                    try:
                        data = sock.recv(RECV_BUFF_S)
                        self.__notify_all("test", [self.server_sock, sock])
                        logger.debug(f"User sent data: {data}")
                    except ConnectionResetError:
                        logger.info("A client has disconnected")
                        self.__notify_all("A user has disconnected")
                        sock.close()
                        self.inputs.remove(sock)
                    except Exception as e:
                        logger.exception(e)
                        self.inputs.remove(sock)
                        logger.error(f"Client exited: {sock.getpeername()}")
                        sock.close()

    def __greet(self, client: socket):
        logger.debug("Greet")
        names = [n.getpeername() for n in self.inputs if n is not client and n is not self.server_sock]
        greetMsg = "Hello user!\n"
        client.send(greetMsg.encode())

    def __notify_all(self, message: str, non_receptors: [socket]):
        logger.debug("Notify all")
        for connection in self.inputs:
            if connection not in non_receptors:
                logger.debug(f"Sending {message} to {connection}")
                connection.send(message.encode())
