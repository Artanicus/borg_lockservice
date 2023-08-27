from absl import flags
import os
import sys
import uvicorn

from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer

import subprocess
import pathlib

# Get all directories under the given paths
def get_available_repos(directory: str) -> list[pathlib.Path]:
    path = pathlib.Path(directory)
    return [f for f in path.iterdir() if f.is_dir()]


FLAGS = flags.FLAGS
app = FastAPI()
auth = HTTPBearer()

PREFIX = "BORG_LOCKSERVICE"

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
flags.mark_flag_as_required('repodir')

FLAGS(sys.argv)
BEARER_TOKEN = FLAGS.token
REPOS: list[pathlib.Path] = get_available_repos(FLAGS.repodir)


@app.get("/")
async def root():
    return {
        "message": PREFIX,
    }


@app.get("/lock/{repo}")
async def lock(
    repo: str,
    token: Annotated[str, Depends(auth)],
    timeout_seconds: int = 3600,
    duration_minutes: int = 45,
):
    if token.credentials == BEARER_TOKEN:
        repo_path: pathlib.Path = get_repo_path(repo)
        if repo_path:
            acquire_lock(repo_path, timeout_seconds, duration_minutes)
            return {"message": f"Locked {repo} for a max of {duration_minutes}m"}
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
    return {"repos": REPOS}


def get_repo_path(target: str) -> pathlib.Path:
    for repo in REPOS:
        if repo.name == target:
            return repo
    return None

def acquire_lock(repo: pathlib.Path, timeout_seconds: int, duration_minutes: int):
    try:
        subprocess.run(
            [
                "borg",
                "with-lock",
                f"--lock-wait={timeout_seconds}",
                repo,
                "sleep",
                f"{duration_minutes}m",
            ]
        )
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=423)  # 423: Locked


def run():
    uvicorn.run(
        "borg_lockservice:app", host=FLAGS.host, port=FLAGS.port, reload=FLAGS.dev
    )


if __name__ == "__main__":
    run()
