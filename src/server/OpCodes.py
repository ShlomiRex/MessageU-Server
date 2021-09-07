from enum import Enum


class RequestCodes(Enum):
	REQC_REGISTER_USER = 1000
	REQC_CLIENT_LIST = 1001
	REQC_PUB_KEY = 1002
	REQC_SEND_TEXT = 1003
	REQC_WAITING_MSGS = 1004
