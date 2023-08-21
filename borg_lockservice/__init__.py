from absl import flags, logging, app
import os, sys
import uvicorn


FLAGS = flags.FLAGS

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


async def main(scope, receive, send):
    assert scope['type'] == 'http'

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', b'text/plain'],
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': bytes(f"Hewwo World :3 .. I'm listening on {FLAGS.port}", 'utf-8'),
    })


def run_uvicorn(argv):
    del argv
    logging.info(f"Will listen on {FLAGS.host}:{FLAGS.port}")
    uvicorn.run("borg_lockservice:main", host=FLAGS.host, port=FLAGS.port)

# script endpoint installed by package
def run():
    app.run(run_uvicorn)


if __name__ == "__main__":
    run()
