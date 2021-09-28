import select
from socket import socket
import logging

from Database.Database import Database, UserNotExistDBException
from Server.OpCodes import ResponseCodes, RequestCodes, MessageTypes
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_REQUEST_HEADER, S_PUBLIC_KEY, S_MESSAGE_TYPE, \
    S_CONTENT_SIZE, S_MESSAGE_ID

from Server.Request import RequestHeader, unpack_request_header
from Server.Response import BaseResponse, MessageResponse, ResponsePayload_PullMessage

SELECT_TIMEOUT = 1
logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    def __init__(self, message: str):
        super.__init__(message)


class Server:
    def __init__(self, port: int, ip: str = "127.0.0.1", max_clients_queue: int = 5):
        """
        Creates the server that listens to multiple clients. To start run the 'start' function.
        :param port: Port to bind to
        :param ip: Ip to bind to
        :param max_clients_queue: Maximum concurrent users in queue (if over, server refuses to server new user)
        """
        self.version = 2
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
            for client_socket in readable:
                if client_socket is self.server_sock:
                    client, address = self.server_sock.accept()

                    # Set blocking. Threads deal with blocking.
                    client.setblocking(True)  #TODO: Test
                    self.inputs.append(client)
                    logger.info(f"New client connection from: {address}")
                else:
                    try:
                        self.__handle_request(client_socket)
                    except (ConnectionResetError, ConnectionAbortedError):
                        logger.info("A client has disconnected")

                        client_socket.close()
                        self.inputs.remove(client_socket)
                    except Exception as e:
                        logger.exception(e)

                        logger.info("Sending error message to client...")
                        self.__send_error(client_socket)

                        logger.error(f"Forcing connection close with client: {client_socket.getpeername()}")
                        client_socket.close()
                        self.inputs.remove(client_socket)
        logger.info("Server finished running")
        self.server_sock.close()

    def shutdown(self):
        self._is_running = False

    def __receive_request_header(self, sock: socket) -> RequestHeader:
        logger.debug("Receiving request header...")
        buff = sock.recv(S_REQUEST_HEADER)
        if len(buff) == 0:
            raise ConnectionAbortedError("Couldn't receive request header!")
        return unpack_request_header(buff)

    def __send_error(self, client_socket: socket):
        logger.info("Sending error response...")
        response = BaseResponse(self.version, ResponseCodes.RESC_ERROR, 0, None)
        packet = response.pack()
        client_socket.sendall(packet)

    def __handle_request(self, client_socket: socket):
        header = self.__receive_request_header(client_socket)
        logger.debug(f"Header: {header}")

        logger.info("Handling request")

        if header.code == RequestCodes.REQC_REGISTER_USER:
            self.__handle_register_request(client_socket)

        # Update user last seen
        # We do this after registering, because user doesn't exist on DB if not registered.
        self.database.update_last_seen(header.clientId.hex())

        if header.code == RequestCodes.REQC_CLIENT_LIST:
            self.__handle_client_list_request(client_socket, header)

        elif header.code == RequestCodes.REQC_PUB_KEY:
            self.__handle_pub_key_request(client_socket)

        elif header.code == RequestCodes.REQC_SEND_MESSAGE:
            self.__handle_send_message_request(client_socket, header)

        elif header.code == RequestCodes.REQC_WAITING_MSGS:
            self.__handle_pull_waiting_messages(client_socket, header)

        else:
            raise ValueError("Request code: " + str(header.code) + " is not recognized.")


    def __handle_register_request(self, client_socket: socket):
        logger.info("Handling register request...")

        username = client_socket.recv(S_USERNAME).decode().rstrip('\x00')
        pub_key = client_socket.recv(S_PUBLIC_KEY)

        # First check is name in database
        try:
            register_success, client_id = self.database.register_user(username, pub_key)
            response = BaseResponse(self.version, ResponseCodes.RESC_REGISTER_SUCCESS, S_CLIENT_ID, client_id)
            self.__send_packet(client_socket, response)
        except UserNotExistDBException:
            self.__send_error(client_socket)

        logger.info("Finished handling register request.")

    def __handle_client_list_request(self, client_socket: socket, header: RequestHeader):
        logger.info("Handling client list request...")

        # Get users to send
        users = self.database.get_all_users()
        # Minus 1 because registered user will not get his own data.
        payload_size = (S_CLIENT_ID + S_USERNAME) * (len(users) - 1)

        # Send first packet which contains headers and payload size.
        response = BaseResponse(self.version, ResponseCodes.RESC_LIST_USERS, payload_size, None)
        packet = response.pack()
        client_socket.send(packet)

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

    def __send_packet(self, client_socket: socket, response: BaseResponse):
        packet = response.pack()
        logger.debug(f"Sending response (parsed): {response}")
        client_socket.sendall(packet)
        logger.debug("Sent!")

    def __handle_pub_key_request(self, client_socket: socket):
        logger.info("Handling public key request...")
        client_id = client_socket.recv(S_CLIENT_ID)

        pub_key = self.database.get_user_by_client_id(client_id.hex())[3]
        pub_key_bytes = bytes.fromhex(pub_key)
        payload = client_id + pub_key_bytes
        response = BaseResponse(self.version, ResponseCodes.RESC_PUBLIC_KEY, S_CLIENT_ID + S_PUBLIC_KEY, payload)
        self.__send_packet(client_socket, response)

    def __handle_send_message_request(self, client_socket: socket, header: RequestHeader):
        logger.info("Handling send message request...")

        # Get message header
        dst_client_id = client_socket.recv(S_CLIENT_ID)
        message_type = client_socket.recv(S_MESSAGE_TYPE)
        content_size = client_socket.recv(S_CONTENT_SIZE)

        # Process
        message_type_int = int.from_bytes(message_type, "little", signed=False)
        try:
            message_type_enum = MessageTypes(message_type_int)
        except Exception:
            raise ValueError(
                f"Couldn't parse message type to enum. Message type: {message_type_int} is not recognized.")
        to_client = dst_client_id
        from_client = header.clientId
        content_size_int = int.from_bytes(content_size, "little", signed=False)

        logger.info(f"Request message from: {from_client.hex(' ', 2)} to: {to_client.hex(' ', 2)}")

        # Check type
        if message_type_enum == MessageTypes.REQ_SYMMETRIC_KEY:
            logger.info("Handling get symmetric key request...")

            # No message content then. Check if no content (must be zero)
            if content_size_int != 0:
                raise ProtocolError(
                    f"Expected content of size 0 in symmetric key request, instead got content size: {content_size_int}")

            msg_content = None

        elif message_type_enum == MessageTypes.SEND_FILE:
            logger.info("Handling send file request...")

            msg_content = client_socket.recv(content_size_int)

        else:
            # Else - we already check enum. If type is not castable to the enum, then we throw there exception. So it's fine to ask 'else'.
            logger.info("Handling send text message request...")

            msg_content = client_socket.recv(content_size_int)

        # Insert message
        success, message_id = self.database.insert_message(to_client.hex(), from_client.hex(), message_type_int, msg_content)

        # Check insertion success
        if not success:
            self.__send_error(client_socket)
        else:
            payload_size = S_CLIENT_ID + S_MESSAGE_ID
            payload = MessageResponse(dst_client_id, message_id)
            response = BaseResponse(self.version, ResponseCodes.RESC_SEND_TEXT, payload_size, payload)
            self.__send_packet(client_socket, response)

    def __handle_pull_waiting_messages(self, client_socket: socket, header: RequestHeader):
        logger.info("Handling pull messages request...")
        # No request payload. No need to read from socket.

        # The one who send this request, we take all of the messages that have 'to_client' equal to him.
        requestee = header.clientId.hex()
        db_messages = self.database.get_messages(requestee)

        payload = b''

        if db_messages is not None and len(db_messages) != 0:
            for db_message in db_messages:
                # Unpack tuple
                _id, to_client, from_client, _type, content_size, content = db_message

                # Process
                type_enum = MessageTypes(_type)
                from_client_bytes = bytes.fromhex(from_client)

                # Create payload
                _payload = ResponsePayload_PullMessage(from_client_bytes, _id, type_enum, content_size, content)
                packet = _payload.pack()
                payload += packet

                # Delete from database
                self.database.delete_message(_id)

        response = BaseResponse(self.version, ResponseCodes.RESC_WAITING_MSGS, len(payload), payload)
        self.__send_packet(client_socket, response)
