from enum import Enum


class SocketMessage(Enum):
    LOCK_ACQUIRED = b"LOCK_ACQUIRED"
    LOCK_LOST = b"LOCK_LOST"
    KEEPALIVE = b"KEEPALIVE"
