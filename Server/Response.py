from dataclasses import dataclass
import struct

from Server.OpCodes import ResponseCodes


@dataclass
class BaseResponse:
    version: int
    code: ResponseCodes
    payloadSize: int
    payload: bytes

    def pack(self) -> bytes:
        if self.payload and len(self.payload) > 0:
            fmt = f"<cHI{self.payloadSize}s"
            return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize, self.payload)
        else:
            fmt = f"<cHI"
            return struct.pack(fmt, self.version.to_bytes(1, "little", signed=False), self.code.value, self.payloadSize)

# @dataclass
# class RegisterResponse:
#     clientId: int
#     baseResponse: BaseResponse
#
#     def pack(self) -> bytes:
#         buff = b''
#
#         pass