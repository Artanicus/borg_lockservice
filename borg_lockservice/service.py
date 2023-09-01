from absl import flags
import os
import sys
import uvicorn
import logging

from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.logger import logger
from contextlib import asynccontextmanager

import subprocess
from pathlib import Path

import socket
import tempfile
from . import SocketMessage, Lock

FLAGS = flags.FLAGS
PREFIX = "BORG_LOCKSERVICE"
auth = HTTPBearer()

flags.DEFINE_string(
    "token",
    os.getenv(f"{PREFIX}_TOKEN", None),
    "Bearer token required to access the API.",
)

flags.DEFINE_string(
    "repodir",
    os.getenv(f"{PREFIX}_REPODIR", None),
    "Directory containing repos.",
)

flags.DEFINE_string(
    "host",
    os.getenv(f"{PREFIX}_HOST", "0.0.0.0"),
    "Listen address for the host.",
)

flags.DEFINE_integer(
    "port",
    os.getenv(f"{PREFIX}_PORT", 8000),
    "Listen port for the service. Defaults to 8000",
)

flags.DEFINE_boolean(
    "dev",
    os.getenv(f"{PREFIX}_DEV", False),
    "Enable development mode. Defaults to False, should not be enabled in production.",
)

flags.mark_flag_as_required("token")
flags.mark_flag_as_required("repodir")


@asynccontextmanager
async def lifespan(app: FastAPI):
    FLAGS(sys.argv)
    app.repos = get_available_repos(FLAGS.repodir)  # type: ignore[attr-defined]
    app.locks = {}  # type: ignore[attr-defined]
    yield


FLAGS(sys.argv)
app = FastAPI(lifespan=lifespan)
log = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG if FLAGS.dev else logging.INFO)


@app.get("/")
async def root():
    return {
        "message": PREFIX,
    }


@app.get("/lock/{repo}")
async def lock(
    repo: str,
    token: Annotated[HTTPAuthorizationCredentials, Depends(auth)],
    timeout_seconds: int = 3600,
):
    if token.credentials == FLAGS.token:
        repo_path: Optional[Path] = get_repo_path(repo)
        if repo_path:
            # Listen for messaging from the envoy to confirm a lock has been acquired
            with tempfile.TemporaryDirectory() as socket_dir:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout_seconds)
                sock_path = socket_dir / Path(f"{PREFIX}_envoy.sock")
                start_envoy(repo_path, sock_path, timeout_seconds)
                log.info(f"Started envoy, waiting on {sock_path}")
                sock.bind(bytes(sock_path))
                log.info("waiting for a connection")
                sock.listen(1)
                try:
                    connection, _ = sock.accept()
                    log.debug("Envoy connected")
                except socket.timeout:
                    log.info("Envoy timed out, cannot acquire lock!")
                    raise HTTPException(status_code=423)  # HTTP error: Locked
                try:
                    while True:
                        data = connection.recv(16)
                        log.debug(f"Received: {str(data)}")
                        if not data:
                            log.debug("Transmission done")
                            break
                        else:
                            if data == SocketMessage.LOCK_ACQUIRED.value:
                                log.info("Envoy confirmed lock")
                                app.locks[repo] = Lock(
                                    socket=sock_path, pid=42, locked=True
                                )  # type: ignore[attr-defined]
                                break

                finally:
                    connection.close()
            return {"message": f"Locked {repo}."}
        else:
            raise HTTPException(status_code=404)
    else:
        raise HTTPException(status_code=403)


@app.get("/unlock/{repo}")
async def unlock(repo: str):
    return {"message": "Not yet implemented"}


@app.get("/status/{repo}")
async def status(repo: str):
    return {"message": "Not yet implemented"}


@app.get("/list")
async def list_locks():
    return {"repos": app.locks}  # type: ignore[attr-defined]


# Get all directories under the given paths
def get_available_repos(directory: str) -> list[Path]:
    path = Path(directory)
    return [f for f in path.iterdir() if f.is_dir()]


def get_repo_path(target: str) -> Optional[Path]:
    for repo in app.repos:  # type: ignore[attr-defined]
        if repo.name == target:
            return repo
    return None


def start_envoy(repo: Path, socket: Path, timeout_seconds: int):
    log.debug(f"Envoy launching for {socket}")
    subprocess.Popen(
        [
            "borg",
            "with-lock",
            f"--lock-wait={timeout_seconds}",
            repo,
            "lockservice_envoy",
            f"--socket={socket}",
        ]
    )


def run():
    FLAGS(sys.argv)
    uvicorn.run(
        "borg_lockservice.service:app",
        host=FLAGS.host,
        port=FLAGS.port,
        reload=FLAGS.dev,
        log_level="debug" if FLAGS.dev else "info",
        workers=5 if not FLAGS.dev else 1,
    )


if __name__ == "__main__":
    run()
