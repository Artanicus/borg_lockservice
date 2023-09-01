from enum import Enum
from dataclasses import dataclass
from pathlib import Path


class SocketMessage(Enum):
    LOCK_ACQUIRED = b"LOCK_ACQUIRED"
    LOCK_LOST = b"LOCK_LOST"
    KEEPALIVE = b"KEEPALIVE"


@dataclass
class Lock:
    socket: Path
    pid: int
    locked: bool = False
