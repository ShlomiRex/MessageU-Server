import logging
import socket
import threading
import time

from Database.Database import Database, UserNotExistDBException
from Server import LOGGER_FORMAT_THREAD, LOGGER_DATE_FORMAT
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_REQUEST_HEADER, S_PUBLIC_KEY, S_MESSAGE_TYPE, \
    S_CONTENT_SIZE, S_MESSAGE_ID, SERVER_VERSION, S_RECV_BUFF, S_RECV_CIPHER_BUFF
from Server.Request import RequestHeader, unpack_request_header
from Server.OpCodes import ResponseCodes, RequestCodes, MessageTypes
from Server.Response import BaseResponse, MessageResponse, ResponsePayload_PullMessage


logger = logging.getLogger(__name__)
logger.propagate = False  # We add custom format, so we don't want to propagate the message to the root logger (duplicate messages)

logger_handler = logging.StreamHandler()  # Handler for the logger
logger_handler.setFormatter(logging.Formatter(LOGGER_FORMAT_THREAD, datefmt=LOGGER_DATE_FORMAT))
logger.addHandler(logger_handler)

# Shared mutex object between worker threads
database = Database()


class ProtocolError(Exception):
    def __init__(self, message: str):
        super.__init__(message)


class ClientWorker(threading.Thread):
    def __init__(self, client_socket: socket, on_close):
        super(ClientWorker, self).__init__()
        self.version = SERVER_VERSION

        self.client_socket = client_socket
        self.on_close = on_close

    def run(self) -> None:
        logger.info("Running worker...")

        try:
            header = self.__receive_request_header()
            logger.debug(f"Header: {header}")

            logger.info("Handling request")

            # Unregistered API
            if header.code == RequestCodes.REQC_REGISTER_USER:
                self.__handle_register_request()

            # Registered API
            else:
                # Update user last seen
                database.update_last_seen(header.clientId.hex())

                if header.code == RequestCodes.REQC_CLIENT_LIST:
                    self.__handle_client_list_request(header)

                elif header.code == RequestCodes.REQC_PUB_KEY:
                    self.__handle_pub_key_request()

                elif header.code == RequestCodes.REQC_SEND_MESSAGE:
                    self.__handle_send_message_request(header)

                elif header.code == RequestCodes.REQC_WAITING_MSGS:
                    self.__handle_pull_waiting_messages(header)

                else:
                    raise ValueError("Request code: " + str(header.code) + " is not recognized.")

            # Call callback
            self.on_close(self)
        except (ConnectionResetError, ConnectionAbortedError):
            logger.info("A client has disconnected")

            self.client_socket.close()
        except Exception as e:
            logger.exception(e)

            logger.info("Sending error message to client...")
            self.__send_error()

            logger.error(f"Forcing connection close with client: {self.client_socket.getpeername()}")
            self.client_socket.close()

    def __handle_request(self):
        header = self.__receive_request_header()
        logger.debug(f"Header: {header}")

        logger.info("Handling request")

        if header.code == RequestCodes.REQC_REGISTER_USER:
            self.__handle_register_request()

        # Update user last seen
        # We do this after registering, because user doesn't exist on DB if not registered.
        database.update_last_seen(header.clientId.hex())

        if header.code == RequestCodes.REQC_CLIENT_LIST:
            self.__handle_client_list_request(header)

        elif header.code == RequestCodes.REQC_PUB_KEY:
            self.__handle_pub_key_request()

        elif header.code == RequestCodes.REQC_SEND_MESSAGE:
            self.__handle_send_message_request(header)

        elif header.code == RequestCodes.REQC_WAITING_MSGS:
            self.__handle_pull_waiting_messages(header)

        else:
            raise ValueError("Request code: " + str(header.code) + " is not recognized.")

    def __handle_register_request(self):
        logger.info("Handling register request...")

        username = self.client_socket.recv(S_USERNAME).decode().rstrip('\x00')
        pub_key = self.client_socket.recv(S_PUBLIC_KEY)

        # First check is name in database
        try:
            register_success, client_id = database.register_user(username, pub_key)

            response = BaseResponse(self.version, ResponseCodes.RESC_REGISTER_SUCCESS, S_CLIENT_ID, client_id)
            self.__send_response(response)
        except UserNotExistDBException:
            self.__send_error()

        logger.info("Finished handling register request.")

    def __handle_client_list_request(self, header: RequestHeader):
        logger.info("Handling client list request...")

        # Get users to send
        users = database.get_all_users()
        # Minus 1 because registered user will not get his own data.
        payload_size = (S_CLIENT_ID + S_USERNAME) * (len(users) - 1)

        # Send first packet which contains headers and payload size.
        response = BaseResponse(self.version, ResponseCodes.RESC_LIST_USERS, payload_size, None)
        packet = response.pack()
        self.client_socket.send(packet)

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
            self.client_socket.send(payload)

        logger.info("Finished handling users list request.")

    def __handle_pub_key_request(self):
        logger.info("Handling public key request...")
        client_id = self.client_socket.recv(S_CLIENT_ID)

        pub_key = database.get_user_by_client_id(client_id.hex())[3]

        pub_key_bytes = bytes.fromhex(pub_key)
        payload = client_id + pub_key_bytes
        response = BaseResponse(self.version, ResponseCodes.RESC_PUBLIC_KEY, S_CLIENT_ID + S_PUBLIC_KEY, payload)
        self.__send_response(response)

    def __handle_pull_waiting_messages(self, header: RequestHeader):
        logger.info("Handling pull messages request...")
        # No request payload. No need to read from socket.

        # The one who send this request, we take all of the messages that have 'to_client' equal to him.
        requestee = header.clientId.hex()
        db_messages = database.get_messages(requestee)

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
                database.delete_message(_id)

        response = BaseResponse(self.version, ResponseCodes.RESC_WAITING_MSGS, len(payload), payload)
        self.__send_response(response)

    def __handle_encrypted_chunks(self, content_size: int, message_id: int) -> bool:
        """
        This function is used for handling encrypted file and large text messages.
        :param content_size:
        :param message_id:
        :param dst_client_id:
        :return: Success
        """
        # Get chunk by chunk.
        bytes_left_to_recv = content_size
        logger.info(f"Reading encrypted chunks (Totaling: {content_size} bytes)...")

        # NOTE: Yuval says in the forum : https://opal.openu.ac.il/mod/ouilforum/discuss.php?d=2977367&p=7101326#p7101326
        # That it's fine to load the file to RAM and just push to DB. I spent 2 days trying to append chunks to SQLite.
        # I also think, if we weren't allowed to collect the entire file to RAM, that appending chunks is still wrong.
        # SQLite is long term storage, not 'ram' like storage device. It affect performance for each query run.
        stitched_chunks = b''

        while bytes_left_to_recv > 0:
            # Get cipher
            if bytes_left_to_recv > S_RECV_CIPHER_BUFF:
                cipher = self.client_socket.recv(S_RECV_CIPHER_BUFF)
            else:
                cipher = self.client_socket.recv(bytes_left_to_recv)
            # Stitch
            stitched_chunks += cipher
        logger.debug(f"Finished stitching chunks! (Stitch length: {len(stitched_chunks)} bytes)")

        logger.info("Inserting stitched chunks into DB...")
        success = database.set_message_content(message_id, stitched_chunks)
        if not success:
            logger.error("Insertion failed!")
            self.__send_error()
            return False
        logger.debug("Insertion success!")
        return True

    # Send text message + send request for symm key + send your symm key
    def __handle_send_message_request(self, header: RequestHeader):
        # TODO: I need to test this entire function. Everything is changed.
        logger.info("Handling send message request...")

        # Get message header
        dst_client_id = self.client_socket.recv(S_CLIENT_ID)
        message_type = self.client_socket.recv(S_MESSAGE_TYPE)
        content_size = self.client_socket.recv(S_CONTENT_SIZE)

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

        # Log the correct message
        if message_type_enum == MessageTypes.SEND_FILE:
            logger.info("Handling send file request...")
        elif message_type_enum == MessageTypes.SEND_TEXT_MESSAGE:
            logger.info("Handling send text message request...")
        elif message_type_enum == MessageTypes.REQ_SYMMETRIC_KEY:
            logger.info("Handling get symmetric key request...")
        elif message_type_enum == MessageTypes.SEND_SYMMETRIC_KEY:
            logger.info("Handling send symmetric key request...")
        else:
            raise ValueError(f"Invalid message type: {message_type_enum}")

        # Sanitize protocol
        if message_type_enum == MessageTypes.REQ_SYMMETRIC_KEY:
            if content_size_int != 0:
                raise ProtocolError(f"Expected content of size 0 in 'get symmetric key' request, instead got content size: {content_size_int}")
        elif message_type_enum == MessageTypes.SEND_SYMMETRIC_KEY:
            if content_size_int == 0:
                raise ProtocolError(f"Expected to receive symmetric key from client, but content size is 0.")

        logger.info(f"Request message from: '{from_client.hex()}' to: '{to_client.hex()}', content size: {content_size_int}")

        # In any case, insert message with empty payload (if we need to insert payload, we update the row later)
        logger.debug("Inserting message to DB...")
        success, message_id = database.insert_message(to_client.hex(), from_client.hex(), message_type_int, None)
        # Check insertion success
        if not success:
            logger.error("Failed to insert!")
            self.__send_error()
            return

        # Check if we need to insert any payload.

        # Check if message has encrypted payload. In both cases, we deal with encrypted chunks.
        if message_type_enum in (MessageTypes.SEND_FILE, MessageTypes.SEND_TEXT_MESSAGE):
            self.__handle_encrypted_chunks(content_size_int, message_id)
        # Check if we need to receive symmetric key.
        elif message_type_enum == MessageTypes.SEND_SYMMETRIC_KEY:
            symm_key_enc = self.client_socket.recv(content_size_int)

            logger.info("Inserting symmetric key into DB...")
            success = database.set_message_content(message_id, symm_key_enc)
            if not success:
                logger.error("Insertion failed!")
                self.__send_error()
                return

        # Done handling each case. Send OK response.
        payload_size = S_CLIENT_ID + S_MESSAGE_ID
        payload = MessageResponse(dst_client_id, message_id)
        response = BaseResponse(self.version, ResponseCodes.RESC_SEND_MESSAGE, payload_size, payload)
        self.__send_response(response)

    def __receive_request_header(self) -> RequestHeader:
        logger.debug("Receiving request header...")
        buff = self.client_socket.recv(S_REQUEST_HEADER)
        if len(buff) == 0:
            raise ConnectionAbortedError("Couldn't receive request header!")
        return unpack_request_header(buff)

    def __send_error(self):
        logger.info("Sending error response...")
        response = BaseResponse(self.version, ResponseCodes.RESC_ERROR, 0, None)
        packet = response.pack()
        self.client_socket.sendall(packet)

    def __send_response(self, response: BaseResponse):
        packet = response.pack()
        logger.debug(f"Sending response (parsed): {response}")
        self.client_socket.sendall(packet)
        logger.debug("Sent!")
