from Server.OpCodes import MessageTypes
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_PUBLIC_KEY
import re

USERNAME_BLACKLIST_SUBSTRINGS = [
    "DROP TABLE",
    "INSERT INTO",
    "DELETE FROM",
    "CREATE TABLE",
]

USERNAME_BLACKLIST_REGEX = [
    r'SELECT (\w+|\*) FROM .*'
]

USERNAME_ALLOWED_ASCII_START = 32
USERNAME_ALLOWED_ASCII_END = 127

class UsersSanitizer:
    @staticmethod
    def username(username):
        if username is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(username, str):
            raise TypeError("Username must be string.")

        if len(username) not in range(1, S_USERNAME + 1):
            raise ValueError(f"Username must be at least 1 character and at most {S_USERNAME + 1} characters.")

        for blacklisted_word in USERNAME_BLACKLIST_SUBSTRINGS:
            if blacklisted_word.lower() in username.lower():
                raise ValueError(f"Username: '{username}' contains black listed word: '{blacklisted_word}'")

        for blacklisted_regex in USERNAME_BLACKLIST_REGEX:
            if re.match(blacklisted_regex, username, re.IGNORECASE):
                raise ValueError(f"Username: '{username}' contains black listed regex: '{blacklisted_regex}'")

        # Check allowed characters
        for c in username:
            if ord(c) not in range(USERNAME_ALLOWED_ASCII_START, USERNAME_ALLOWED_ASCII_END + 1):
                raise ValueError(f"Username: '{username}' contains disallowed character: '{c}' with ascii value: {ord(c)}")

    @staticmethod
    def client_id(client_id_hex):
        if client_id_hex is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(client_id_hex, str):
            raise TypeError("Client ID must be string.")

        try:
            int(client_id_hex, 16)
        except ValueError:
            raise ValueError(f"Client ID must be represented in hex.")

        if len(client_id_hex) != S_CLIENT_ID * 2:
            raise ValueError(f"Client ID must be represented in {S_PUBLIC_KEY} bytes hex.")

    @staticmethod
    def pub_key(pub_key_hex):
        if pub_key_hex is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(pub_key_hex, str):
            raise TypeError("Public Key must be string.")

        try:
            int(pub_key_hex, 16)
        except ValueError:
            raise ValueError(f"Public Key must be represented in hex.")

        if len(pub_key_hex) != S_PUBLIC_KEY * 2:
            raise ValueError(f"Public Key must be represented in {S_PUBLIC_KEY} bytes hex.")

    @staticmethod
    def last_seen(unix_epoch):
        if unix_epoch is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(unix_epoch, int):
            raise TypeError("Last seen must be int.")


class MessagesSanitizer:
    @staticmethod
    def message_type(_type):
        if _type is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(_type, int):
            raise TypeError("Username must be int.")

        try:
            MessageTypes(_type)
        except Exception:
            raise ValueError("Message Type value isn't in protocol specification.")

    @staticmethod
    def content_size(content_size):
        pass

    @staticmethod
    def content(content_size, content):
        if content is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(content, bytes):
            raise TypeError("Content must be bytes.")

        MessagesSanitizer.content_size(content_size)
        if len(content) != content_size:
            raise ValueError("Size of content is not equal to content size.")

    @classmethod
    def id(cls, _id):
        if _id is None:
            raise ValueError("Database input must be set. None is not allowed.")

        if not isinstance(_id, int):
            raise TypeError("Message ID must be integer.")

        if _id < 0:
            raise ValueError("Message ID can't be negative.")
