import sqlite3
import logging
import time
import uuid
from typing import Optional

from Database import MODULE_LOGGER_NAME, DB_LOCATION
from .Queries import *

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

    def registerUser(self, username: str, pub_key: bytes) -> tuple[bool, bytes]:
        logger.info("Registering user: " + str(username))
        row = self.getUser(username)
        if row is None:
            # No user exist. Add.
            logger.debug("No such username in database. Adding...")
            unix_epoch = int(time.time())
            pub_key_hex = pub_key.hex()
            client_id = uuid.uuid4()
            client_id_hex = client_id.hex
            sql = QUERY_INSERT_USER.format(username=username, client_id=client_id_hex, public_key=pub_key_hex,
                                           last_seen=unix_epoch)
            cur = self._conn.cursor()
            cur.execute(sql)
            self._conn.commit()
            logger.debug("Added user to DB!")
            return True, client_id.bytes
        else:
            logger.error("Can't register user: already in database.")
            return False, b''

    def getUser(self, username: str):
        sql = QUERY_FIND_USERNAME.format(username=username)
        cur = self._conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        return row

    def truncateDB(self):
        # For testing purposes only.
        logger.warning("Truncating database...!")
        sql1 = QUERY_TRUNCATE_TRABLE_Users
        sql2 = QUERY_TRUNCATE_TRABLE_Messages
        cur = self._conn.cursor()
        cur.execute(sql1)
        cur.execute(sql2)
        self._conn.commit()
        logger.warning("OK")

    def getAllUsers(self) -> [tuple[str, str]]:
        cur = self._conn.cursor()
        cur.execute(QUERY_SELECT_ALL_USERS)
        res = cur.fetchall()
        return res

    def isClientIdExists(self, client_id: str) -> bool:
        sql = QUERY_SELECT_USER_BY_CLIENT_ID.format(client_id=client_id)
        cur = self._conn.cursor()
        cur.execute(sql)
        res = cur.fetchone()
        if res is None or len(res) == 0:
            return False
        else:
            return True

    def getUserByClientId(self, client_id: str) -> tuple[int, str, str, str, int]:
        """
        Query DB and return single user from Users table.
        :param client_id:
        :return: Id (int), ClientId (hex str), Username (str), Public Key (hex str), Last seen (unix epoch int)
        """
        sql = QUERY_SELECT_USER_BY_CLIENT_ID.format(client_id=client_id)
        cur = self._conn.cursor()
        cur.execute(sql)
        res = cur.fetchone()

        if res is None or len(res) == 0:
            raise UserNotExistDBException()
        else:
            return res

    def insertMessage(self, to_client: str, from_client: str, message_type: int, content_size: int, content: Optional[bytes]) -> bool:
        logger.debug(f"Inserting message from: {from_client} to: {to_client}")
        if content_size > 0:
            sql = QUERY_INSERT_MESSAGE.format(to_client=to_client, from_client=from_client,
                                              type=message_type, content_size=content_size, content=content)
        else:
            sql = QUERY_INSERT_MESSAGE_WITHOUT_CONTENT.format(to_client=to_client, from_client=from_client, type=message_type)
        cur = self._conn.cursor()
        cur.execute(sql)
        self._conn.commit()
        res = cur.fetchone()

        if cur.rowcount != 1:
            logger.error("Failed to insert a row!")
            return False
        else:
            return True



class UserNotExistDBException(Exception):
    pass
