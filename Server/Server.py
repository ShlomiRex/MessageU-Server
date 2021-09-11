import select
from socket import socket
import logging

from Database.Database import Database
from Server.OpCodes import ResponseCodes
from Server.ProtocolDefenitions import S_RECV_BUFF, S_USERNAME, S_CLIENT_ID

from Server.Request import parseRequest, RegisterUserRequest, UsersListRequest
from Server.Response import BaseResponse

SELECT_TIMEOUT = 1
logger = logging.getLogger(__name__)


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

        self.inputs = [server_sock]  # Read from sockets
        self.server_sock = server_sock
        self.outputs = []  # Write to sockets

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
                else:
                    try:
                        self.__read_sock(sock)
                    except (ConnectionResetError, ConnectionAbortedError):
                        logger.info("A client has disconnected")
                        sock.close()
                        self.inputs.remove(sock)
                    except Exception as e:
                        logger.exception(e)
                        self.inputs.remove(sock)
                        logger.error(f"Client exited: {sock.getpeername()}")
                        sock.close()
        logger.info("Server finished running")
        self.server_sock.close()

    def __read_sock(self, sock: socket):
        logger.debug("Reading from socket")
        data = sock.recv(S_RECV_BUFF)
        if len(data) == 0:
            logger.info("Socket has 0 bytes to read! Client has performed orderly shutdown!")
            raise ConnectionAbortedError("recv() returned 0 bytes read (shutdown of the connection)")
        logger.debug(f"User sent data ({len(data)} bytes): {data}")
        try:
            self.__handle_request(sock, data)
        except Exception as e:
            logger.exception(e)
            self.__send_error(sock)

    def __send_error(self, client_socket: socket):
        logger.warning("Sending error response...")
        response = BaseResponse(self.version, ResponseCodes.RESC_ERROR, 0, b'')
        packet = response.pack()
        client_socket.sendall(packet)
        logger.warning("OK")

    def __handle_request(self, client_socket: socket, data: bytes):
        logger.info("Handling request")
        request = parseRequest(data)
        logger.info("Request (unpacked): " + str(request))
        try:
            if isinstance(request, RegisterUserRequest):
                logger.info("Handling register request...")
                # First check is name in database
                registerSuccess, clientId = self.database.registerUser(request.name, request.pub_key)
                if registerSuccess:
                    response = BaseResponse(self.version, ResponseCodes.RESC_REGISTER_SUCCESS, S_CLIENT_ID, clientId)
                    self.__send_packet(client_socket, response)
                else:
                    self.__send_error(client_socket)
            elif isinstance(request, UsersListRequest):
                logger.info("Handling list users request...")
                users = self.database.getAllUsers()
                payload_size = (S_CLIENT_ID + S_USERNAME) * len(users)

                # Send first packet which contains headers and payload size.
                response = BaseResponse(self.version, ResponseCodes.RESC_LIST_USERS, payload_size, None)
                first_packet = response.pack()
                client_socket.send(first_packet)

                # Send the rest of the payload in chunks
                for client_id, username in users:
                    client_id_payload = bytes.fromhex(client_id)
                    username_null_padded_payload = username.ljust(S_USERNAME, '\0')
                    payload = client_id_payload + username_null_padded_payload.encode()
                    client_socket.send(payload)

            else:
                raise TypeError("A request must be one of the request classes.")
        except Exception as e:
            logger.exception(e)
            self.__send_error(client_socket)

    def __send_packet(self, client_socket: socket, response: BaseResponse):
        payload = response.pack()
        logger.info(f"Sending response ({len(payload)} bytes): {payload}")
        logger.info(f"Response (parsed): {response}")
        client_socket.sendall(payload)
        logger.info("Sent!")

    def shutdown(self):
        self._is_running = False
