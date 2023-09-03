from typing import Optional

from aiocache import Cache
import psutil
import signal
import os

import borg_lockservice as service


class Lock:
    __repo: str
    cache: Cache

    @classmethod
    async def create(
        cls, repo: str, pid: int, redis_host: str, redis_port: int
    ) -> "Lock":
        if not psutil.pid_exists(pid):
            raise ValueError(f"Not a valid pid: {pid}")

        self = Lock()
        self.__repo = repo
        self.cache = Cache(
            Cache.REDIS,
            endpoint=redis_host,
            port=redis_port,
            namespace=f"{service.PREFIX}:{repo}",
        )
        await self.cache.set("pid", pid)
        return self

    @classmethod
    async def find(
        cls, repo: str, redis_host: str, redis_port: int, pid: Optional[int] = None
    ) -> Optional["Lock"]:
        if pid and not psutil.pid_exists(pid):
            return None

        self = Lock()
        self.cache = Cache(
            Cache.REDIS,
            endpoint=redis_host,
            port=redis_port,
            namespace=f"{service.PREFIX}:{repo}",
        )

        value = await self.cache.get("pid")
        if (pid and value and pid == value) or (not pid and value):
            self.__repo = repo
            return self
        return None

    @property
    def repo(self) -> str:
        return self.__repo

    @property
    async def pid(self) -> int:
        return await self.cache.get("pid")

    async def kill(self) -> None:
        pid = await self.pid
        os.kill(pid, signal.SIGTERM)

    async def terminate(self) -> None:
        await self.cache.delete("pid")
