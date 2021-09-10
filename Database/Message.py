from dataclasses import dataclass


@dataclass
class Message:
    id: int
    to_client: int
    from_client: int
    type: int
    content: str
