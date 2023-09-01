from absl import flags, app, logging

from fastapi import FastAPI, HTTPException
from pathlib import Path

import socket
import sys
import time
from datetime import datetime, timedelta

from . import SocketMessage

FLAGS = flags.FLAGS

PREFIX = "BORG_LOCKSERVICE"

flags.DEFINE_string(
    "socket",
    None,
    "Path to unix socket for service communications.",
)

flags.mark_flag_as_required("socket")

SOCKET = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)


def main(argv):
    del argv

    try:
        SOCKET.connect(FLAGS.socket)
    except socket.error as error:
        logging.error(f"Failed opening comms socket {FLAGS.socket}: {error}")
        sys.exit(1)

    try:
        # Signal that the envoy has launched, i.e. the lock has been acquired
        SOCKET.sendall(SocketMessage.LOCK_ACQUIRED.value)
    except socket.error as error:
        logging.error(f"Failed writing to comms socket {FLAGS.socket}: {error}")
        sys.exit(1)

    while True:
        time.sleep(60)


def signal_handler(sig, frame):
    logging.info(f"Exiting gracefully for {sig}")
    SOCKET.sendall(SocketMessage.EXITING.value)
    SOCKET.close()


def run():
    app.run(main)


if __name__ == "__main__":
    run()
