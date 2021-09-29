import socket
import logging

from Server.ClientWorker import ClientWorker

logger = logging.getLogger(__name__)





class Server:
    def __init__(self, port: int, ip: str = "127.0.0.1"):
        """
        Creates the server that listens to multiple clients. To start run the 'start' function.
        :param port: Port to bind to
        :param ip: Ip to bind to
        """
        self.port = port
        self.ip = ip

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((self.ip, self.port))

        self.workers = []

        # When this set to False, stops the server.
        self._is_running = False

    def start(self):
        """
        Starts the server.
        :return:
        """
        self._is_running = True
        self.server_sock.listen()

        logger.info(f"Server is listening on: {self.ip}:{self.port}")
        while self._is_running:
            client_socket, address = self.server_sock.accept()

            logger.info(f"New client connection from: {address}")

            # On worker finish, he calls this
            def on_worker_close(_worker: ClientWorker):
                self.workers.remove(_worker)

            worker = ClientWorker(client_socket, on_worker_close)
            self.workers.append(worker)
            logger.debug(f"Number of currently working threads: {len(self.workers)}")
            worker.start()

        logger.info("Server finished running")
        for w in self.workers:
            w.join()
        self.server_sock.close()

    def shutdown(self):
        self._is_running = False

