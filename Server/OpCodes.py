from enum import Enum


class RequestCodes(Enum):
	REQC_REGISTER_USER = 1000
	REQC_CLIENT_LIST = 1001
	REQC_PUB_KEY = 1002
	REQC_SEND_MESSAGE = 1003
	REQC_WAITING_MSGS = 1004

class ResponseCodes(Enum):
	RESC_REGISTER_SUCCESS = 2000
	RESC_LIST_USERS = 2001
	RESC_PUBLIC_KEY = 2002
	RESC_SEND_MESSAGE = 2003
	RESC_WAITING_MSGS = 2004
	RESC_ERROR = 9000

class MessageTypes(Enum):
	REQ_SYMMETRIC_KEY = 1
	SEND_SYMMETRIC_KEY = 2
	SEND_TEXT_MESSAGE = 3
	SEND_FILE = 4