import threading
import time
import unittest
import socket

from Server.Server import Server

IP = "127.0.0.1"
PORT = 8080
# Request: register shlomi with 0 clientId (ignored)
REGISTER_USER_REQUEST_PACKET = "0000000000000000000000000000000002e803a700000073686c6f6d690030819d300d06092a864886f70d010101050003818b0030818702818100ab51760fb35c5d0efccd85fa6ef68e369ecae4165bcd6797c0e5e59b71f6987e8070349d65556fbb645c746f7b7dc0018fb23acb44644bd35a50ab8cd1bd96813ab192581e02ff8351b2a4743dd762fa19b657ea66f458bf8bd4dcc0dc9b27940cd47719bfe222a50eede6bfdda35d25a949ec021b7f5fa6f3e9c0e8c8072475020111"

# Start server before running tests
global server

def start_server():
    global server
    server = Server(PORT, ip=IP)

    # Clear database
    server.database.truncateDB()
    server.database.create_db()

    server.start()
threading.Thread(target=start_server).start()

time.sleep(1) # Let DB initialize

class MainTestingClass(unittest.TestCase):
    def test_registerUser(self):
        global server
        buff = bytes.fromhex(REGISTER_USER_REQUEST_PACKET)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((IP, PORT))

        self.assertIsNone(server.database.getUser("shlomi"))

        sock.sendall(buff) # Insert 'shlomi' user
        time.sleep(1)

        self.assertIsNotNone(server.database.getUser("shlomi"))

        sock.close()

    @classmethod
    def tearDownClass(cls) -> None:
        global server
        server.shutdown()
