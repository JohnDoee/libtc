import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from libtc import DelugeClient

from .basetest import *

@pytest.fixture(
    scope="module",
    params=[
        True,
        False,
    ],
)
def client(request):
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        auth_path = tmp_path / "auth"
        p = subprocess.Popen(["deluged", "-c", str(tmp_path), "-d", "-L", "debug"])
        for _ in range(30):
            if auth_path.exists() and auth_path.stat().st_size > 0:
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to get deluge auth")

        with auth_path.open() as f:
            username, password = f.read().split("\n")[0].split(":")[:2]

        client = DelugeClient("127.0.0.1", 58846, username, password, tmp_path)
        if request.param:
            with client.client as c:
                c.core.enable_plugin("Label")
            client.label = "testlabel"
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start deluge")
        yield client
        p.kill()


def test_serialize_configuration(client):
    url = client.serialize_configuration()
    url, query = url.split("?")
    assert re.match(r"deluge://localclient:[a-f0-9]{40}@127.0.0.1:58846", url)
    assert query.startswith("session_path=")
