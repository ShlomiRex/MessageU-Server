FILE_PORT = "port.info"
S_RECV_BUFF = 1024  # Amount of bytes to read at once from socket.
S_RECV_CIPHER_BUFF = int(((S_RECV_BUFF / 16) + 1) * 16) # Amount of bytes to recv from AES CBS encryption algorithm, given the plain message is of S_RECV_BUFF size. Used for chunking.

S_CLIENT_ID = 16
S_USERNAME = 255
S_PUBLIC_KEY = 160

S_REQUEST_HEADER = 23

# Message related
S_MESSAGE_TYPE = 1
S_CONTENT_SIZE = 4
S_MESSAGE_ID = 4

SERVER_VERSION = 2
