from absl import flags
import os, sys
import uvicorn

from fastapi import FastAPI

FLAGS = flags.FLAGS
app = FastAPI()

PREFIX = "BORG_LOCKSERVICE"

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


@app.get("/")
async def root():
    return {
        'message': f"uwu :3",
    }


def run():
    FLAGS(sys.argv)
    uvicorn.run("borg_lockservice:app", host=FLAGS.host, port=FLAGS.port, reload=FLAGS.dev)


if __name__ == "__main__":
    run()
