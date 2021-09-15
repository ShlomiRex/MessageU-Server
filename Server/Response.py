from dataclasses import dataclass
import struct
from typing import Union, Optional

from Server.OpCodes import ResponseCodes
from Server.ProtocolDefenitions import S_CLIENT_ID, S_MESSAGE_ID


@dataclass
class MessageResponse:
    destClientId: bytes
    messageId: int

    def pack(self) -> bytes:
        fmt = f"<{S_CLIENT_ID}sI"
        #msgId = self.messageId.to_bytes(S_MESSAGE_ID, "little", signed=False)
        return struct.pack(fmt, self.destClientId, self.messageId)

@dataclass
class BaseResponse:
    version: int
    code: ResponseCodes
    payloadSize: int
    payload: Union[bytes, MessageResponse, None]

    def pack(self) -> bytes:
        if self.payload is not None:
            # We have payload
            if isinstance(self.payload, bytes):
                if len(self.payload) > 0:
                    fmt = f"<cHI{self.payloadSize}s"
                    return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize, self.payload)
                else:
                    raise ValueError("Length of payload is 0 but payload is not None!")
            elif isinstance(self.payload, MessageResponse):
                fmt = f"<cHI{self.payloadSize}s"
                payload = self.payload.pack()
                return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize, payload)
            else:
                raise ValueError("Instance of payload is not recognized.")
        else:
            # We don't have payload
            fmt = f"<cHI"
            return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize)
