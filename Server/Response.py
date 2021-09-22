from dataclasses import dataclass
import struct
from typing import Union, Optional

from Server.OpCodes import ResponseCodes, MessageTypes
from Server.ProtocolDefenitions import S_CLIENT_ID, S_MESSAGE_ID


@dataclass
class ResponsePayload_PullMessage:
    from_client_id: bytes
    messageId: int
    messageType: MessageTypes
    messageSize: int
    content: Optional[bytes]

    def pack(self):
        if self.content is None or self.content == b'':
            return struct.pack(f"<{S_CLIENT_ID}sIBI", self.from_client_id, self.messageId, self.messageType.value, self.messageSize)
        else:
            return struct.pack(f"<{S_CLIENT_ID}sIBI{self.messageSize}s", self.from_client_id, self.messageId, self.messageType.value, self.messageSize, self.content)


@dataclass
class MessageResponse:
    destClientId: bytes
    messageId: int

    def pack(self) -> bytes:
        fmt = f"<{S_CLIENT_ID}sI"
        return struct.pack(fmt, self.destClientId, self.messageId)


@dataclass
class BaseResponse:
    version: int
    code: ResponseCodes
    payloadSize: int
    payload: Union[bytes, MessageResponse, list[ResponsePayload_PullMessage], None]

    def __pack_no_payload(self):
        fmt = f"<cHI"
        return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize)

    def __pack_with_payload(self, packet: bytes):
        fmt = f"<cHI{self.payloadSize}s"
        return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize, packet)

    def pack(self) -> bytes:
        if self.payload is not None:
            # We have payload - check instance of payload
            if isinstance(self.payload, bytes):
                if len(self.payload) > 0:
                    return self.__pack_with_payload(self.payload)
                else:
                    if self.payload == b'':
                        return self.__pack_no_payload()
                    else:
                        raise ValueError("Length of payload is 0 but payload is not None!")
            elif isinstance(self.payload, MessageResponse):
                # We don't change self.payload. For esthetics.
                return self.__pack_with_payload(self.payload.pack())
            else:
                raise ValueError("Instance of payload is not recognized.")
        else:
            # We don't have payload
            return self.__pack_no_payload()
