import select
import sys
from socket import socket
import logging

from src.database.Database import Database

from src.server.Request import parseRequest, RegisterUserRequest

RECV_BUFF_S = 1024      # Amount of bytes to read at once from socket.
SELECT_TIMEOUT = 1
logger = logging.getLogger("Server")

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

        server_sock = socket()
        server_sock.bind((self.ip, self.port))
        server_sock.listen(max_clients_queue)
        server_sock.setblocking(False)

        self.inputs = [server_sock]     # Read from sockets
        self.server_sock = server_sock
        self.outputs = []               # Write to sockets

        self.database = Database()
        # When this set to False, stops the server.
        self._is_running = False

    def start(self):
        """
        Starts the server.
        :return:
        """
        self._is_running = True
        logger.info(f"Server is listening on: {self.ip}:{self.port}")
        while self._is_running and self.inputs:
            readable, writeable, exceptions = select.select(self.inputs, [], [], SELECT_TIMEOUT)
            for sock in readable:
                if sock is self.server_sock:
                    client, address = self.server_sock.accept()
                    self.inputs.append(client)
                    logger.info(f"New client connection from: {address}")
                    #self.__greet(client)
                    #self.__notify_all(f"Client {address} has joined the chat\n", [self.server_sock, client])
                else:
                    try:
                        self.__read_sock(sock)
                    except ConnectionResetError or ConnectionAbortedError:
                        logger.info("A client has disconnected")
                        #self.__notify_all("A user has disconnected", [self.server_sock, sock])
                        sock.close()
                        self.inputs.remove(sock)
                    except Exception as e:
                        logger.exception(e)
                        self.inputs.remove(sock)
                        logger.error(f"Client exited: {sock.getpeername()}")
                        sock.close()
        logger.info("Server finished running")
        self.server_sock.close()

    # def __greet(self, client: socket):
    #     logger.debug("Greeting user")
    #     names = [n.getpeername() for n in self.inputs if n is not client and n is not self.server_sock]
    #     greetMsg = "Hello user!\n"
    #     client.send(greetMsg.encode())

    # def __notify_all(self, message: str, non_receptors: [socket]):
    #     logger.debug("Notifying all")
    #     for connection in self.inputs:
    #         if connection not in non_receptors:
    #             logger.debug(f"Sending {message} to {connection}")
    #             connection.send(message.encode())

    def __read_sock(self, sock: socket):
        logger.info("Reading from socket")
        data = sock.recv(RECV_BUFF_S)
        #self.__notify_all("notify all test message", [self.server_sock, sock])
        logger.debug(f"User sent data ({len(data)} bytes): {data}")
        try:
            self.__handle_request(data)
        except Exception as e:
            logger.exception(e)
            self.__send_error()

    def __send_error(self):
        #TODO: Send error response
        pass

    def __handle_request(self, data):
        request = parseRequest(data)
        logger.info("Request (unpacked): " + str(request))

        if isinstance(request, RegisterUserRequest):
            # First check is name in database
            uname_exists_or_internal_errors = self.database.registerUser(request.name, request.pub_key)
            if uname_exists_or_internal_errors:
                self.__send_error()
        else:
            raise TypeError("A request must be one of the request classes.")

    def shutdown(self):
        self._is_running = False