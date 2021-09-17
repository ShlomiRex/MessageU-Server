import sqlite3
import logging
import time
import uuid
from typing import Optional

from Database import MODULE_LOGGER_NAME, DB_LOCATION
from .Queries import *
from Database.Sanitizer import UsersSanitizer, MessagesSanitizer

logger = logging.getLogger(MODULE_LOGGER_NAME)


class Database:
    def __init__(self):
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
        cur.execute(QUERY_CREATE_USERS_TABLE)
        self._conn.commit()
        logger.debug("OK")

        logger.debug("Creating Messages table...")
        cur.execute(QUERY_CREATE_MESSAGES_TABLE)
        self._conn.commit()
        logger.debug("OK")

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
            sql = QUERY_INSERT_USER.format(username=username, client_id=client_id_hex, public_key=pub_key_hex, last_seen=unix_epoch)
            cur = self._conn.cursor()
            cur.execute(sql)
            self._conn.commit()
            logger.debug("Added user to DB!")
            return True, client_id.bytes
        else:
            raise UserNotExistDBException()

    def get_user(self, username: str):
        UsersSanitizer.username(username)
        sql = QUERY_FIND_USERNAME.format(username=username)
        cur = self._conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        return row

    def get_all_users(self) -> [tuple[str, str]]:
        cur = self._conn.cursor()
        cur.execute(QUERY_SELECT_ALL_USERS)
        res = cur.fetchall()
        return res

    def is_client_exists(self, client_id: str) -> bool:
        UsersSanitizer.client_id(client_id)
        sql = QUERY_SELECT_USER_BY_CLIENT_ID.format(client_id=client_id)
        cur = self._conn.cursor()
        cur.execute(sql)
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
        sql = QUERY_SELECT_USER_BY_CLIENT_ID.format(client_id=client_id)
        cur = self._conn.cursor()
        cur.execute(sql)
        res = cur.fetchone()

        if res is None or len(res) == 0:
            raise UserNotExistDBException()
        else:
            return res

    def insert_message(self, to_client: str, from_client: str, message_type: int, content_size: int, content: Optional[bytes]) -> (bool, Optional[int]):
        logger.debug(f"Inserting message from: {from_client} to: {to_client}")

        UsersSanitizer.client_id(to_client)
        UsersSanitizer.client_id(from_client)
        MessagesSanitizer.message_type(message_type)
        MessagesSanitizer.content_size(content_size)
        if content_size > 0:
            MessagesSanitizer.content(content_size, content)
            sql = QUERY_INSERT_MESSAGE.format(to_client=to_client, from_client=from_client, type=message_type, content_size=content_size, content=content)
        else:
            sql = QUERY_INSERT_MESSAGE_WITHOUT_CONTENT.format(to_client=to_client, from_client=from_client, type=message_type)
        cur = self._conn.cursor()
        cur.execute(sql)
        self._conn.commit()

        message_id = cur.lastrowid

        if cur.rowcount != 1:
            logger.error("Failed to insert a row!")
            return False
        else:
            return True, message_id

    def get_messages(self, to_client: str):
        UsersSanitizer.client_id(to_client)
        sql = QUERY_MESSAGES_TO_CLIENT.format(client_id=to_client)
        cur = self._conn.cursor()
        cur.execute(sql)
        res = cur.fetchall()

        return res

    def deleteMessage(self, _id):
        MessagesSanitizer.id(_id)
        sql = QUERY_DELETE_MESSAGE.format(id=_id)
        cur = self._conn.cursor()
        logger.debug(f"Deleting message: {_id}")
        cur.execute(sql)
        self._conn.commit()


class UserNotExistDBException(Exception):
    pass
