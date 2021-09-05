import datetime
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    public_key: str
    last_seen: datetime.datetime
