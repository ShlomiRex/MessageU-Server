import sqlite3
import logging
import threading
import time
import uuid
from typing import Optional

from Database import MODULE_LOGGER_NAME, DB_LOCATION
from Database.Sanitizer import UsersSanitizer, MessagesSanitizer
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_PUBLIC_KEY

logger = logging.getLogger(MODULE_LOGGER_NAME)


class Database():
    def __init__(self):
        super().__init__()
        logger.debug("Connecting...")
        self._conn = sqlite3.connect(DB_LOCATION, check_same_thread=False)  # Multiple threads can use same cursor
        logger.debug("Connected!")

        self.create_db()

    def create_db(self):
        """
        If exception occurs, we can't continue with the server, so we don't handle exceptions at this time
        :return:
        """
        logger.info("Creating database...")
        cur = self._conn.cursor()

        logger.debug("Creating Users table...")

        # TODO: Add 'varchar(255)' to username (name)
        # TODO: Check varchar(?) works!
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                client_id varchar({S_CLIENT_ID}) NOT NULL UNIQUE,
                name varchar({S_USERNAME}) NOT NULL,
                public_key varchar({S_PUBLIC_KEY}) NOT NULL,
                last_seen INTEGER
            );
        """)
        self._conn.commit()
        logger.debug("OK")

        logger.debug("Creating Messages table...")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS Messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_client varchar({S_CLIENT_ID}) NOT NULL,
                from_client varchar({S_CLIENT_ID}) NOT NULL,
                type INTEGER NOT NULL,
                content_size INTEGER NOT NULL,
                content blob
            );
            """
        )
        self._conn.commit()

        logger.debug("OK")
        cur.close()

    def register_user(self, username: str, pub_key: bytes) -> tuple[bool, bytes]:
        logger.info("Registering user: " + str(username))

        row = self.get_user(username)

        if row is None:
            # No user exist. Add.
            logger.debug("No such username in database. Adding...")
            unix_epoch = int(time.time())
            pub_key_hex = pub_key.hex()
            client_id = uuid.uuid4()
            client_id_hex = client_id.hex

            UsersSanitizer.username(username)
            UsersSanitizer.client_id(client_id_hex)
            UsersSanitizer.pub_key(pub_key_hex)
            UsersSanitizer.last_seen(unix_epoch)

            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO Users (name, client_id, public_key, last_seen)
                VALUES (?, ?, ?, ?);
            """, [username, client_id_hex, pub_key_hex, unix_epoch])
            self._conn.commit()
            cur.close()
            logger.debug("Added user to DB!")
            return True, client_id.bytes
        else:
            raise UserAlreadyExists(username)

    def get_user(self, username: str):
        UsersSanitizer.username(username)
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Users WHERE name == ?;", [username])
        row = cur.fetchone()
        return row

    def get_all_users(self) -> [tuple[str, str]]:
        cur = self._conn.cursor()
        cur.execute("SELECT client_id, name FROM Users;")
        res = cur.fetchall()
        return res

    def is_client_exists(self, client_id: str) -> bool:
        UsersSanitizer.client_id(client_id)
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Users WHERE client_id=?;", [client_id])
        res = cur.fetchone()
        if res is None or len(res) == 0:
            return False
        else:
            return True

    def get_user_by_client_id(self, client_id: str) -> tuple[int, str, str, str, int]:
        """
        Query DB and return single user from Users table.
        :param client_id:
        :return: Id (int), ClientId (hex str), Username (str), Public Key (hex str), Last seen (unix epoch int)
        """
        UsersSanitizer.client_id(client_id)

        if not self.is_client_exists(client_id):
            raise UserNotExistDBException(client_id)

        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Users WHERE client_id=?;", [client_id])
        res = cur.fetchone()

        if res is None or len(res) == 0:
            raise UserNotExistDBException(client_id)
        else:
            return res

    def insert_message(self, to_client: str, from_client: str, message_type: int, content: Optional[bytes]) -> (bool, Optional[int]):
        """

        :param to_client:
        :param from_client:
        :param message_type:
        :param content:
        :return: Returns tuple. Tuple contains 'success' and 'message_id'.
        """
        logger.debug(f"Inserting message from: {from_client} to: {to_client}")

        UsersSanitizer.client_id(to_client)
        UsersSanitizer.client_id(from_client)
        MessagesSanitizer.message_type(message_type)

        if not self.is_client_exists(to_client):
            raise UserNotExistDBException(to_client)
        if not self.is_client_exists(from_client):
            raise UserNotExistDBException(from_client)

        cur = self._conn.cursor()

        if content is not None and len(content) > 0:
            MessagesSanitizer.content(len(content), content)
            cur.execute(
                """
                    INSERT INTO Messages (to_client, from_client, type, content_size, content) 
                    VALUES (?, ?, ?, ?, ?);
                """, [to_client, from_client, message_type, len(content), sqlite3.Binary(content)])
        else:
            cur.execute(
                """
                    INSERT INTO Messages (to_client, from_client, type, content_size) 
                    VALUES (?, ?, ?, 0);
                """, [to_client, from_client, message_type])
        self._conn.commit()
        message_id = cur.lastrowid
        cur.close()

        if cur.rowcount != 1:
            logger.error("Failed to insert a row!")
            return False
        else:
            return True, message_id

    def get_messages(self, to_client: str):
        UsersSanitizer.client_id(to_client)

        if not self.is_client_exists(to_client):
            raise UserNotExistDBException(to_client)

        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Messages WHERE to_client=?;", [to_client])
        res = cur.fetchall()

        return res

    def delete_message(self, message_id: int):
        MessagesSanitizer.id(message_id)
        cur = self._conn.cursor()
        logger.debug(f"Deleting message: {message_id}")
        cur.execute("DELETE FROM Messages WHERE id=?;", [message_id])
        self._conn.commit()
        cur.close()

    def update_last_seen(self, client_id: str):
        UsersSanitizer.client_id(client_id)

        if not self.is_client_exists(client_id):
            raise UserNotExistDBException(client_id)

        unix_epoch = int(time.time())
        cur = self._conn.cursor()
        cur.execute("UPDATE Users SET last_seen=?;", [unix_epoch])
        self._conn.commit()
        cur.close()

    def set_message_content(self, message_id: int, file: bytes) -> bool:
        MessagesSanitizer.id(message_id)
        cur = self._conn.cursor()

        cur.execute("UPDATE Messages SET content = ? WHERE id = ?;", [file, message_id])

        self._conn.commit()
        cur.close()


class UserNotExistDBException(Exception):
    def __init__(self, client_id: str):
        super().__init__(f"Client: {client_id} doesn't exist on DB!")


class UserAlreadyExists(Exception):
    def __init__(self, username: str):
        super().__init__(f"Client: {username} already exists on DB!")
