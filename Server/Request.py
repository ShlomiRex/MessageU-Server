import logging
from dataclasses import dataclass
import struct

from Server.OpCodes import RequestCodes
from Server.ProtocolDefenitions import S_CLIENT_ID

logger = logging.getLogger(__name__)

@dataclass
class RequestHeader:
    clientId: bytes  # 16 bytes
    version: int  # 1 byte
    code: RequestCodes  # 2 bytes
    payloadSize: int  # 4 bytes


def unpack_request_header(data: bytes) -> RequestHeader:
    # Unpack
    header_fmt = f"<{S_CLIENT_ID}scHI"
    s_header = struct.calcsize(header_fmt)
    client_id, version, code, payload_size = struct.unpack(header_fmt, data[:s_header])

    # Process
    _version = int.from_bytes(version, "little", signed=False)
    _code = RequestCodes(code)

    return RequestHeader(client_id, _version, _code, payload_size)
