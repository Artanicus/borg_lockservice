from absl import flags
from absl import app as absl_app
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
from pathlib import Path

import subprocess
import socket
import tempfile

import borg_lockservice as service
from .lock import Lock

FLAGS = flags.FLAGS
auth = HTTPBearer()

flags.DEFINE_string(
    "token",
    os.getenv(f"{service.PREFIX}_TOKEN", None),
    "Bearer token required to access the API.",
)

flags.DEFINE_string(
    "repodir",
    os.getenv(f"{service.PREFIX}_REPODIR", None),
    "Directory containing repos.",
)

flags.DEFINE_string(
    "host",
    os.getenv(f"{service.PREFIX}_HOST", "0.0.0.0"),
    "Listen address for the host.",
)

flags.DEFINE_integer(
    "port",
    os.getenv(f"{service.PREFIX}_PORT", 8000),
    "Listen port for the service. Defaults to 8000",
)

flags.DEFINE_boolean(
    "dev",
    os.getenv(f"{service.PREFIX}_DEV", False),
    "Enable development mode. Defaults to False, should not be enabled in production.",
)

flags.DEFINE_string(
    "redis_host",
    os.getenv(f"{service.PREFIX}_REDIS_HOST", None),
    "Host portion of a redis server used for keeping state.",
)
flags.DEFINE_integer(
    "redis_port",
    os.getenv(f"{service.PREFIX}_REDIS_PORT", 6379),
    "Port of the redis server.",
)

flags.mark_flag_as_required("token")
flags.mark_flag_as_required("repodir")
flags.mark_flag_as_required("redis_host")


# The lifespan takes care of static state that is not modified by workers
# Any state writes by workers will cause desync! Don't do it!
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Manually init flags so they're available to workers
    FLAGS(sys.argv)
    app.state.repos = get_available_repos(FLAGS.repodir)
    logger.setLevel(logging.DEBUG if FLAGS.dev else logging.INFO)
    app.state.log = logging.getLogger("uvicorn.error")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "state": "OK",
    }


@app.get("/lock/{repo}")
async def lock(
    repo: str,
    token: Annotated[HTTPAuthorizationCredentials, Depends(auth)],
    timeout_seconds: int = 3600,
):
    if token.credentials != FLAGS.token:
        raise HTTPException(status_code=403)

    repo_path: Optional[Path] = get_repo_path(repo)
    if not repo_path:
        raise HTTPException(status_code=404)

    # Listen for messaging from the envoy to confirm a lock has been acquired
    with tempfile.TemporaryDirectory() as socket_dir:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout_seconds)
        sock_path = socket_dir / Path(f"{service.PREFIX}_envoy.sock")
        start_envoy(repo_path, sock_path, timeout_seconds)
        app.state.log.info(f"Started envoy, waiting on {sock_path}")
        sock.bind(bytes(sock_path))
        sock.listen(1)
        try:
            connection, _ = sock.accept()
            app.state.log.debug("Envoy connected")
        except socket.timeout:
            app.state.log.info("Envoy timed out, cannot acquire lock!")
            raise HTTPException(status_code=423)  # HTTP error: Locked
        try:
            while True:
                data = connection.recv(16)
                pid = int.from_bytes(data)
                app.state.log.debug(f"Envoy pid: {pid}")
                if not data:
                    # When transmission ends we stop listening
                    break
                else:
                    app.state.log.info("Envoy confirmed lock")
                    await Lock.create(repo, pid, FLAGS.redis_host, FLAGS.redis_port)
                    break

        finally:
            connection.close()
    return {"state": "locked", "pid": pid}


@app.get("/unlock/{repo}")
async def unlock(
    repo: str,
    pid: int,
    token: Annotated[HTTPAuthorizationCredentials, Depends(auth)],
):
    if token.credentials != FLAGS.token:
        raise HTTPException(status_code=403)
    lock = await Lock.find(
        repo, pid=pid, redis_host=FLAGS.redis_host, redis_port=FLAGS.redis_port
    )
    if not lock:
        raise HTTPException(status_code=404)

    try:
        await lock.kill()  # Kill the envoy releasing the lock
    except OSError as e:
        raise ValueError(f"Unable to kill envoy: {e}")
    finally:
        await lock.terminate()  # Clear lock state from cache
        return {"state": "unlocked"}


@app.get("/status/{repo}")
async def status(
    repo: str,
    token: Annotated[HTTPAuthorizationCredentials, Depends(auth)],
):
    if token.credentials != FLAGS.token:
        raise HTTPException(status_code=403)
    if not get_repo_path(repo):
        raise HTTPException(status_code=404)
    lock = await Lock.find(
        repo, redis_host=FLAGS.redis_host, redis_port=FLAGS.redis_port
    )
    if not lock:
        return {"state": "unknown"}

    return {"state": "locked", "pid": await lock.pid}


@app.get("/list")
async def list_locks(
    token: Annotated[HTTPAuthorizationCredentials, Depends(auth)],
):
    if token.credentials != FLAGS.token:
        raise HTTPException(status_code=403)

    return {"repos": [repo.name for repo in app.state.repos]}


# Get all directories under the given paths
def get_available_repos(directory: str) -> list[Path]:
    path = Path(directory)
    return [f for f in path.iterdir() if f.is_dir()]


def get_repo_path(target: str) -> Optional[Path]:
    for repo in app.state.repos:  # type: ignore[attr-defined]
        if repo.name == target:
            return repo
    return None


def start_envoy(repo: Path, socket: Path, timeout_seconds: int):
    app.state.log.debug(f"Envoy launching for {socket}")
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
    absl_app.run(uvicorn_run)


def uvicorn_run(argv):
    del argv
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
