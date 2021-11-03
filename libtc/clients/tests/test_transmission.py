import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from libtc import TransmissionClient

from .basetest import *


@pytest.fixture(scope="module")
def client():
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        p = subprocess.Popen(
            [
                "transmission-daemon",
                "--config-dir",
                tmp_path,
                "--download-dir",
                tmp_path / "downloads",
                "-T",
                "-f",
            ]
        )

        client = TransmissionClient(
            "http://localhost:9091/transmission/rpc", session_path=str(tmp_path)
        )
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start transmission")
        yield client
        p.kill()


def test_serialize_configuration(client):
    url = client.serialize_configuration()
    url, query = url.split("?")
    assert url == "transmission+http://localhost:9091/transmission/rpc"
    assert query.startswith("session_path=")


def test_auto_configure(client):
    config_path = Path(client.session_path) / "settings.json"
    auto_client = TransmissionClient.auto_configure(config_path)
    assert auto_client.serialize_configuration().replace(
        "localhost", "127.0.0.1"
    ) == client.serialize_configuration().replace("localhost", "127.0.0.1")
