import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from libtc import DelugeClient

from .basetest import *


@pytest.fixture(scope="module")
def client():
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        auth_path = tmp_path / "auth"
        p = subprocess.Popen(["deluged", "-c", str(tmp_path), "-q", "-d"])
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
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start deluge")
        yield client
        p.kill()
