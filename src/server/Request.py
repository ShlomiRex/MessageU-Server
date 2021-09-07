import logging
from dataclasses import dataclass
import struct
from typing import Union

from src.server.OpCodes import RequestCodes

logger = logging.getLogger("Server")


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


def parseRequest(data: bytes) -> Union[RegisterUserRequest]:
    # Unpack
    headerFmt = "<16scHI"
    s_header = struct.calcsize(headerFmt)
    clientId, version, code, payloadSize = struct.unpack(headerFmt, data[:s_header])
    payload = data[s_header:]

    # Process
    clientId = int.from_bytes(clientId, "little", signed=False)
    version = int.from_bytes(version, "little", signed=False)
    reqCode = RequestCodes(code)

    # Return processed request
    base_request = BaseRequest(clientId=clientId, version=version, code=code, payloadSize=payloadSize, payload=payload)

    if reqCode == RequestCodes.REQC_REGISTER_USER:
        term_i = payload.index(0x00)  # Find first null terminator
        name = payload[:term_i].decode()
        pub_key = payload[term_i:term_i + 160]
        request = RegisterUserRequest(name=name, pub_key=pub_key, baseRequest=base_request)
    else:
        logger.error("Could not parse request code: " + str(code))
        raise ValueError("Request code: " + str(code) + " is invalid.")

    return request
