import os
import subprocess
import time
from pathlib import Path

import pytest

from libtc import LilTorrentClient

from .basetest import *
from .test_transmission import client as transmission_client


@pytest.fixture(scope="module")
def client(transmission_client):
    env = os.environ.copy()
    env["LILTORRENT_CLIENT"] = transmission_client.serialize_configuration()
    env["LILTORRENT_APIKEY"] = "secretkey"

    p = subprocess.Popen(["python3", "-m", "libtc.liltorrent"], env=env)

    client = LilTorrentClient("secretkey", "http://127.0.0.1:10977/")
    for _ in range(30):
        if client.test_connection():
            break
        time.sleep(0.1)
    else:
        p.kill()
        pytest.fail("Unable to start liltorrent")

    yield client
    p.kill()
