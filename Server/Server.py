import select
from socket import socket
import logging

from Database.Database import Database, UserNotExistDBException
from Server.OpCodes import ResponseCodes, RequestCodes, MessageTypes
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_REQUEST_HEADER, S_PUBLIC_KEY, S_MESSAGE_TYPE, \
    S_CONTENT_SIZE

from Server.Request import RequestHeader, unpack_request_header
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
            if len(readable) > 0:
                logger.debug(f"Readables: {readable}")
            if len(writeable) > 0:
                logger.debug(f"Writeables: {writeable}")
            if len(exceptions) > 0:
                logger.debug(f"Exceptions: {exceptions}")

            for sock in readable:
                if sock is self.server_sock:
                    client, address = self.server_sock.accept()
                    self.inputs.append(client)
                    logger.info(f"New client connection from: {address}")
                else:
                    try:
                        self.__handle_request(sock)
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

    def __receive_request_header(self, sock: socket) -> RequestHeader:
        logger.debug("Receiving request header...")
        buff = sock.recv(S_REQUEST_HEADER)
        if len(buff) == 0:
            raise ConnectionAbortedError("Couldn't receive request header!")
        return unpack_request_header(buff)

    def __send_error(self, client_socket: socket):
        logger.warning("Sending error response...")
        response = BaseResponse(self.version, ResponseCodes.RESC_ERROR, 0, b'')
        packet = response.pack()
        client_socket.sendall(packet)
        logger.warning("OK")

    def __handle_request(self, client_socket: socket):
        header = self.__receive_request_header(client_socket)
        logger.debug(f"Header: {header}")

        logger.info("Handling request")

        if header.code == RequestCodes.REQC_REGISTER_USER:
            logger.info("Handling register request...")

            username = client_socket.recv(S_USERNAME).decode().rstrip('\x00')
            pub_key = client_socket.recv(S_PUBLIC_KEY)

            # First check is name in database
            register_success, client_id = self.database.registerUser(username, pub_key)
            if register_success:
                response = BaseResponse(self.version, ResponseCodes.RESC_REGISTER_SUCCESS, S_CLIENT_ID, client_id)
                self.__send_packet(client_socket, response)
            else:
                self.__send_error(client_socket)

            logger.info("Finished handling register request.")

        elif header.code == RequestCodes.REQC_CLIENT_LIST:
            logger.info("Handling client list request...")

            # Get users to send
            users = self.database.getAllUsers()
            # Minus 1 because registered user will not get his own data.
            payload_size = (S_CLIENT_ID + S_USERNAME) * (len(users) - 1)

            # Send first packet which contains headers and payload size.
            response = BaseResponse(self.version, ResponseCodes.RESC_LIST_USERS, payload_size, None)
            client_socket.send(response.pack())

            # Send the rest of the payload in chunks
            for client_id, username in users:
                # Convert DB string of hex to bytes.
                client_id_hex_bytes = bytes.fromhex(client_id)

                # Don't send the requestee his own data. Compare bytes to bytes.
                if client_id_hex_bytes == header.clientId:
                    continue

                # Send the user data.
                client_id_payload = bytes.fromhex(client_id)
                username_null_padded_payload = username.ljust(S_USERNAME, '\0')
                payload = client_id_payload + username_null_padded_payload.encode()
                client_socket.send(payload)

            logger.info("Finished handling users list request.")

        elif header.code == RequestCodes.REQC_PUB_KEY:
            logger.info("Handling public key request...")
            client_id = client_socket.recv(S_CLIENT_ID)
            try:
                pub_key = self.database.getUserByClientId(client_id.hex())[3]
                pub_key_bytes = bytes.fromhex(pub_key)
                payload = client_id + pub_key_bytes
                response = BaseResponse(self.version, ResponseCodes.RESC_PUBLIC_KEY, S_CLIENT_ID + S_PUBLIC_KEY, payload)
                self.__send_packet(client_socket, response)
            except UserNotExistDBException:
                self.__send_error(client_socket)

        elif header.code == RequestCodes.REQC_SEND_MESSAGE:
            logger.info("Handling send message request...")

            # Get message header
            dst_client_id = client_socket.recv(S_CLIENT_ID)
            message_type = client_socket.recv(S_MESSAGE_TYPE)
            content_size = client_socket.recv(S_CONTENT_SIZE)

            # Process
            message_type_int = int.from_bytes(message_type, "little", signed=False)
            message_type_enum = MessageTypes(message_type_int)
            content_size_int = int.from_bytes(content_size, "little", signed=False)
            to_client = dst_client_id
            from_client = header.clientId

            # Check type
            if message_type_enum == MessageTypes.REQ_SYMMETRIC_KEY:
                # No message content then

                if content_size_int != 0:
                    logger.error(f"Expected content of size 0 in symmetric key request, instead got content size: {content_size_int}")
                    self.__send_error(client_socket)
                    return

                logger.info(f"Request for symmetric key from: {from_client.hex(' ', 2)} to: {to_client.hex(' ', 2)}")

                # Check recipient exists
                if not self.database.isClientIdExists(dst_client_id.hex()):
                    logger.error("Destination recipient doesn't exist!")
                    self.__send_error(client_socket)
                    return
                else:
                    logger.debug("Destination client id exists!")
                    logger.info("Inserting message to database...")
                    success = self.database.insertMessage(to_client.hex(), from_client.hex(),
                                                          message_type_int, content_size_int, None)
                    if not success:
                        self.__send_error(client_socket)
                    else:
                        logger.info("Success!")
                pass
            else:
                raise ValueError(f"Message type: {message_type} is not recognized.")

        else:
            raise ValueError("Request code: " + str(header.code) + " is not recognized.")


    def __send_packet(self, client_socket: socket, response: BaseResponse):
        payload = response.pack()
        logger.debug(f"Sending response ({len(payload)} bytes): {payload}")
        logger.debug(f"Response (parsed): {response}")
        client_socket.sendall(payload)
        logger.debug("Sent!")

    def shutdown(self):
        self._is_running = False
