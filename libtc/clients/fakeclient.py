import random
import string
from datetime import datetime

import pytz

from ..baseclient import BaseClient
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentState

TORRENTS = {}


def randomString(rng, letters, stringLength):
    return "".join(rng.choice(letters) for i in range(stringLength))


def generate_torrent(rng):
    size = rng.randint(100000, 7000000000)
    return TorrentData(
        randomString(rng, "abcdef0123456789", 40),
        randomString(
            rng, string.ascii_lowercase + " " + "0123456789", rng.randint(10, 26)
        ),
        size,
        TorrentState.ACTIVE,
        100,
        rng.randint(size // 10, size * 20),
        datetime.utcfromtimestamp(rng.randint(1500000000, 1590000000)).astimezone(
            pytz.UTC
        ),
        "example.com",
        rng.randint(0, 500) == 0 and rng.randint(100, 1000000),
        0,
        "",
    )


def touch_torrents(rng, torrents):
    for t in torrents:
        if t.upload_rate > 0:
            t.upload_rate = rng.randint(100, 1000000)
            t.uploaded += t.upload_rate * 10


class FakeClient(BaseClient):
    identifier = "fakeclient"
    display_name = "FakeClient"

    def __init__(self, seed, num_torrents):
        if seed not in TORRENTS:
            rng = random.Random(seed)
            TORRENTS[seed] = {
                "rng": rng,
                "torrents": [generate_torrent(rng) for _ in range(num_torrents)],
            }
        self._torrents = TORRENTS[seed]

    def list(self):
        touch_torrents(self._torrents["rng"], self._torrents["torrents"])
        return self._torrents["torrents"]

    def list_active(self):
        touch_torrents(self._torrents["rng"], self._torrents["torrents"])
        return [t for t in self._torrents["torrents"] if t.upload_rate > 0]

    def start(self, infohash):
        pass

    def stop(self, infohash):
        pass

    def test_connection(self):
        return True

    def add(
        self,
        torrent,
        destination_path,
        fast_resume=False,
        add_name_to_folder=True,
        minimum_expected_data="none",
        stopped=False,
    ):
        pass

    def remove(self, infohash):
        pass

    def retrieve_torrentfile(self, infohash):
        raise FailedToExecuteException("Dummy client does not retrieve torrents")

    def get_download_path(self, infohash):
        raise FailedToExecuteException("No data exist")

    def move_torrent(self, infohash, destination_path):
        raise FailedToExecuteException("Unable to move torrent")

    def get_files(self):
        raise FailedToExecuteException("Unable to get files")

    def move_torrent(self, infohash, destination_path):
        raise FailedToExecuteException("Failed to set path")

    def serialize_configuration(self):
        raise FailedToExecuteException("Unserializable")

    def auto_configure(self):
        raise FailedToExecuteException("Auto configure not available")
