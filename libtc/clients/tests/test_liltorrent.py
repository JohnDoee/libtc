import os
import re
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

    path_mapping = f"{str(transmission_client.session_path / 'from_path')}:{str(transmission_client.session_path / 'to_path')}"
    client = LilTorrentClient(
        "secretkey", "http://127.0.0.1:10977/", path_mapping=path_mapping
    )
    for _ in range(30):
        if client.test_connection():
            break
        time.sleep(0.1)
    else:
        p.kill()
        pytest.fail("Unable to start liltorrent")

    yield client
    p.kill()


def test_serialize_configuration(client):
    url = client.serialize_configuration()
    url, query = url.split("?")
    assert re.match(r"liltorrent\+http://127.0.0.1:10977/", url)
    assert "apikey=secretkey" in query
    assert re.match(r".*path_mapping=.*from_path%3A.*to_path.*", query)


def test_path_mapping(client, testfiles):
    from_path, to_path = list(client.path_mapping.items())[0]

    torrent = testfiles / "Some-Release.torrent"
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b"info"])).hexdigest()
    full_to_path = testfiles / to_path
    full_to_path.mkdir()
    (testfiles / "Some-Release").rename(full_to_path / "Some-Release")
    client.add(torrent_data, testfiles / from_path, fast_resume=False)

    verify_torrent_state(
        client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )
    assert client.get_download_path(infohash) == testfiles / from_path / "Some-Release"
    # TODO: test get_files

    client.remove(infohash)
    verify_torrent_state(client, [])
