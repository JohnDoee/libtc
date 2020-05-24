import pytest
import subprocess
import tempfile
import time

from pathlib import Path

from .basetest import *

from libtc import TransmissionClient


@pytest.fixture(scope="module")
def client():
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        p = subprocess.Popen(["transmission-daemon", "--config-dir", tmp_path, "--download-dir", tmp_path / "downloads", "-T", "-f"])

        client = TransmissionClient("http://localhost:9091/transmission/rpc", str(tmp_path))
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start transmission")
        yield client
        p.kill()
