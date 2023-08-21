from absl import flags
import os
import sys
import uvicorn

from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer


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


FLAGS(sys.argv)
BEARER_TOKEN = FLAGS.token


@app.get("/")
async def root():
    return {
        "message": PREFIX,
    }


@app.get("/lock/{repo}")
async def lock(
    repo: str, token: Annotated[str, Depends(auth)], timeout_minutes: int = 60
):
    if token.credentials == BEARER_TOKEN:
        return {"message": f"Totally locked {repo} for {timeout_minutes}m"}
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
    return {"message": "Not yet implemented"}


def run():
    uvicorn.run(
        "borg_lockservice:app", host=FLAGS.host, port=FLAGS.port, reload=FLAGS.dev
    )


if __name__ == "__main__":
    run()
