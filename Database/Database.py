import sqlite3
import logging
import time
import uuid

from Database import MODULE_LOGGER_NAME, DB_LOCATION
from .Queries import *

logger = logging.getLogger(MODULE_LOGGER_NAME)


class Database:
    def __init__(self):
        logger.debug("Connecting...")
        self._conn = sqlite3.connect(DB_LOCATION, check_same_thread=False) # Multiple threads can use same cursor
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

    def __insert_message(self, to_client: int, from_client: int, type: int, content: str):
        sql = QUERY_INSERT_MESSAGE.format(id=id, to_client=to_client, from_client=from_client, type=type, content=content)
        cur = self._conn.cursor()
        cur.execute(sql)
        self._conn.commit()

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
            sql = QUERY_INSERT_USER.format(username=username, client_id=client_id_hex, public_key=pub_key_hex, last_seen=unix_epoch)
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

