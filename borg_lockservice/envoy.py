from absl import flags, app, logging

import socket
import sys
import time
import os


FLAGS = flags.FLAGS

flags.DEFINE_string(
    "socket",
    None,
    "Path to unix socket for service communications.",
)

flags.mark_flag_as_required("socket")


def main(argv):
    del argv
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.connect(FLAGS.socket)
    except socket.error as error:
        logging.error(f"Failed opening comms socket {FLAGS.socket}: {error}")
        sys.exit(1)

    try:
        # Signal that the envoy has launched, i.e. the lock has been acquired
        # The PID will be stored and used to terminate the envoy
        sock.sendall(os.getpid().to_bytes(16))
    except socket.error as error:
        logging.error(f"Failed writing to comms socket {FLAGS.socket}: {error}")
        sys.exit(1)
    finally:
        sock.close()

    # We're just waiting to be killed to release the lock
    while True:
        time.sleep(60)


def run():
    app.run(main)


if __name__ == "__main__":
    run()
