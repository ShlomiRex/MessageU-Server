import datetime
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    public_key: bytes
    last_seen: datetime.datetime
