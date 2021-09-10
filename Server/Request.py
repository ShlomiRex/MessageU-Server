import logging
from dataclasses import dataclass
import struct
from typing import Union

from Server.OpCodes import RequestCodes
from Server.ProtocolDefenitions import S_USERNAME, S_CLIENT_ID, S_PUBLIC_KEY

logger = logging.getLogger(__name__)


@dataclass
class BaseRequest:
    clientId: int
    version: int
    code: RequestCodes
    payloadSize: int
    payload: bytes

@dataclass
class RegisterUserRequest:
    name: str
    pub_key: bytes
    baseRequest: BaseRequest

@dataclass
class UsersListRequest:
    baseRequest: BaseRequest

def parseRequest(data: bytes) -> Union[RegisterUserRequest, UsersListRequest]:
    # Unpack
    headerFmt = f"<{S_CLIENT_ID}scHI"
    s_header = struct.calcsize(headerFmt)
    clientId, version, code, payloadSize = struct.unpack(headerFmt, data[:s_header])
    payload = data[s_header : s_header + payloadSize]

    # Process
    clientId = int.from_bytes(clientId, "little", signed=False)
    version = int.from_bytes(version, "little", signed=False)
    reqCode = RequestCodes(code)

    # Return processed request
    base_request = BaseRequest(clientId=clientId, version=version, code=code, payloadSize=payloadSize, payload=payload)

    if reqCode == RequestCodes.REQC_REGISTER_USER:
        name = payload[: S_USERNAME].decode().rstrip('\x00')
        pub_key = payload[S_USERNAME : S_USERNAME + S_PUBLIC_KEY]
        request = RegisterUserRequest(name=name, pub_key=pub_key, baseRequest=base_request)
    elif reqCode == RequestCodes.REQC_CLIENT_LIST:
        request = UsersListRequest(base_request)
    else:
        logger.error("Could not parse request code: " + str(code))
        raise ValueError("Request code: " + str(code) + " is invalid.")

    return request
