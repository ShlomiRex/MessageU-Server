"""
Note: last_seen is INT it represents UNIX epoch time
"""

QUERY_CREATE_USERS_TABLE = """
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name text NOT NULL,
            public_key text,
            last_seen INTEGER
        );
"""

QUERY_CREATE_MESSAGES_TABLE = """
        CREATE TABLE IF NOT EXISTS Messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_client INTEGER NOT NULL,
            from_client INTEGER NOT NULL,
            type INTEGER NOT NULL,
            content blob NOT NULL
        );
"""

QUERY_INSERT_MESSAGE = """
    INSERT INTO Messages (to_client, from_client, type, content) 
    VALUES ({to_client}, {from_client}, {type}, '{content}');
"""

QUERY_SELECT_FROM_MESSAGES = """
    SELECT * FROM Messages ORDER BY id DESC LIMIT 5;
"""