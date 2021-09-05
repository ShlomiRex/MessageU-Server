import sqlite3
import logging

from .Message import Message
from .Queries import QUERY_CREATE_USERS_TABLE, QUERY_CREATE_MESSAGES_TABLE, QUERY_INSERT_MESSAGE, \
    QUERY_SELECT_FROM_MESSAGES

logger = logging.getLogger("Database")

DB_LOCATION = "server.db"


class Database:
    def __init__(self):
        logger.debug("Connecting...")
        self.conn = sqlite3.connect(DB_LOCATION)
        logger.debug("Connected!")

        self.__create_db()
        self.__insert_dummy_data()
        self.__log_messages_table()

    def __create_db(self):
        """
        If exception occurs, we can't continue with the server, so we don't handle exceptions at this time
        :return:
        """
        cur = self.conn.cursor()

        logger.debug("Creating Users table...")
        cur.execute(QUERY_CREATE_USERS_TABLE)
        self.conn.commit()
        logger.debug("OK")
        logger.debug("Creating Messages table...")
        cur.execute(QUERY_CREATE_MESSAGES_TABLE)
        self.conn.commit()
        logger.debug("OK")

    def __log_messages_table(self):
        cur = self.conn.cursor()
        c = cur.execute(QUERY_SELECT_FROM_MESSAGES)
        rows = cur.fetchall()

        for row in rows:
            m = Message(*row)   # What this does is, it unpacks the tuple (row) so we can send multiple arguments.
            logger.debug(m)

    def __insert_message(self, to_client: int, from_client: int, type: int, content: str):
        sql = QUERY_INSERT_MESSAGE.format(id=id, to_client=to_client, from_client=from_client, type=type, content=content)
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def __insert_dummy_data(self):
        self.__insert_message(100, 12312312321, 5, "ABCCC")



