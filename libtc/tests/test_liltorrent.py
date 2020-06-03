import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
import pytz

from libtc import FailedToExecuteException, bdecode, liltorrent
from libtc.baseclient import BaseClient
from libtc.torrent import TorrentData, TorrentState

GLOBAL_CONFIG = {
    "headers": {"Authorization": f"Bearer testkey"},
}
TORRENT_DATA = (
    b"d8:announce42:udp://tracker.opentrackr.org:1337/announce10:creat"
    b"ed by13:mktorrent 1.04:infod6:lengthi11e4:name10:file_a.txt12:pi"
    b"ece lengthi262144e6:pieces20:Qy\xdb=Bc\xc9\xcbN\xcf\x0e\xdb\xc6S"
    b"\xcaF\x0e6x\xb77:privatei1eee"
)
TORRENT_LIST = [
    TorrentData(
        "a" * 40,
        "test 1",
        1000,
        TorrentState.ACTIVE,
        100.0,
        10,
        datetime(2020, 1, 1, 0, 0, 0, tzinfo=pytz.UTC),
        "example.com",
        10,
        0,
        "",
    ),
    TorrentData(
        "b" * 40,
        "test 2",
        2000,
        TorrentState.STOPPED,
        0.0,
        0,
        datetime(2020, 1, 2, 0, 0, 0, tzinfo=pytz.UTC),
        "example.com",
        0,
        10,
        "",
    ),
]


class DummyClient(BaseClient):
    identifier = "dummyclient"

    def __init__(self):
        self._call_log = []

    def list(self):
        return TORRENT_LIST

    def list_active(self):
        return [TORRENT_LIST[0]]

    def start(self, infohash):
        self._call_log.append(("start", infohash))

    def stop(self, infohash):
        self._call_log.append(("stop", infohash))

    def test_connection(self):
        return True

    def add(
        self,
        torrent,
        destination_path,
        fast_resume=False,
        add_name_to_folder=True,
        minimum_expected_data="none",
    ):
        self._call_log.append(
            (
                "add",
                torrent,
                destination_path,
                fast_resume,
                add_name_to_folder,
                minimum_expected_data,
            )
        )

    def remove(self, infohash):
        self._call_log.append(("remove", infohash))

    def retrieve_torrentfile(self, infohash):
        return TORRENT_DATA

    def get_download_path(self, infohash):
        return Path("/download/path")

    def serialize_configuration(self):
        raise FailedToExecuteException("Not supported")

    def auto_configure(self):
        raise FailedToExecuteException("Not supported")


def get_client():
    return GLOBAL_CONFIG["client"]


liltorrent.get_client = get_client


@pytest.fixture
def client():
    os.environ["LILTORRENT_APIKEY"] = "testkey"
    GLOBAL_CONFIG["client"] = DummyClient()
    with liltorrent.app.test_client() as client:
        yield client


def test_bad_apikey(client):
    r = client.post(
        "/start?infohash=0123456789abcdef",
        headers={"Authorization": "Bearer badkeyhere"},
    )
    assert r.status_code == 401
    assert len(GLOBAL_CONFIG["client"]._call_log) == 0


def test_list(client):
    r = client.get("/list", headers=GLOBAL_CONFIG["headers"])
    assert [TorrentData.unserialize(t).__dict__ for t in json.loads(r.data)] == [
        t.__dict__ for t in TORRENT_LIST
    ]


def test_list_active(client):
    r = client.get("/list_active", headers=GLOBAL_CONFIG["headers"])
    assert [TorrentData.unserialize(t).__dict__ for t in json.loads(r.data)] == [
        t.__dict__ for t in TORRENT_LIST[:1]
    ]


def test_start(client):
    r = client.post(
        "/start?infohash=0123456789abcdef", headers=GLOBAL_CONFIG["headers"]
    )
    assert GLOBAL_CONFIG["client"]._call_log[0] == ("start", "0123456789abcdef")


def test_stop(client):
    r = client.post("/stop?infohash=0123456789abcdef", headers=GLOBAL_CONFIG["headers"])
    assert GLOBAL_CONFIG["client"]._call_log[0] == ("stop", "0123456789abcdef")


def test_test_connection(client):
    r = client.get("/test_connection", headers=GLOBAL_CONFIG["headers"])
    assert json.loads(r.data) == True


def test_add(client):
    r = client.post(
        "/add?destination_path=%2Ftmp%2Fhorse&fast_resume=true&add_name_to_folder=true&minimum_expected_data=full",
        content_type="multipart/form-data",
        headers=GLOBAL_CONFIG["headers"],
        data={"torrent": (BytesIO(TORRENT_DATA), "torrent")},
    )
    call_entry = GLOBAL_CONFIG["client"]._call_log[0]
    assert call_entry[0] == "add"
    assert call_entry[1] == bdecode(TORRENT_DATA)
    assert call_entry[2] == Path("/tmp/horse")
    assert call_entry[3] == True
    assert call_entry[4] == True
    assert call_entry[5] == "full"


def test_remove(client):
    r = client.post(
        "/remove?infohash=0123456789abcdef", headers=GLOBAL_CONFIG["headers"]
    )
    assert GLOBAL_CONFIG["client"]._call_log[0] == ("remove", "0123456789abcdef")


def test_retrieve_torrent_file(client):
    r = client.get(
        "/retrieve_torrentfile?infohash=0123456789abcdef",
        headers=GLOBAL_CONFIG["headers"],
    )
    assert r.data == TORRENT_DATA
    assert "0123456789abcdef.torrent" in r.headers["Content-Disposition"]
    assert r.headers["Content-Type"] == "application/x-bittorrent"


def test_get_download_path(client):
    r = client.get("/get_download_path", headers=GLOBAL_CONFIG["headers"])
    assert json.loads(r.data) == "/download/path"
