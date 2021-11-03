from collections import namedtuple

from ...baseclient import BaseClient
from ...exceptions import FailedToExecuteException

TestTorrent = namedtuple(
    "TestTorrent",
    [
        "torrent_data",
        "torrent_files",
        "download_path",
        "torrent_file_data",
        "is_active",
    ],
)


class TestClient(BaseClient):
    identifier = "testclient"
    display_name = "TestClient"

    def __init__(self):
        self._action_queue = []
        self._test_connection = True
        self._torrents = {}

    def list(self):
        return [t.torrent_data for t in self._torrents.values()]

    def list_active(self):
        return [t.torrent_data for t in self._torrents.values() if t.is_active]

    def start(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        self._action_queue.append(("start", {"infohash": infohash}))

    def stop(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        self._action_queue.append(("stop", {"infohash": infohash}))

    def test_connection(self):
        return self._test_connection

    def add(
        self,
        torrent,
        destination_path,
        fast_resume=False,
        add_name_to_folder=True,
        minimum_expected_data="none",
        stopped=False,
    ):
        self._action_queue.append(
            (
                "add",
                {
                    "torrent": torrent,
                    "destination_path": destination_path,
                    "fast_resume": fast_resume,
                    "add_name_to_folder": add_name_to_folder,
                    "minimum_expected_data": minimum_expected_data,
                    "stopped": stopped,
                },
            )
        )

    def remove(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        self._action_queue.append(("remove", {"infohash": infohash}))

    def retrieve_torrentfile(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        return self._torrents[infohash].torrent_file_data

    def get_download_path(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        return self._torrents[infohash].download_path

    def get_files(self, infohash):
        if infohash not in self._torrents:
            raise FailedToExecuteException("Torrent does not exist")
        return self._torrents[infohash].torrent_files

    def serialize_configuration(self):
        return f"{self.identifier}://"

    def auto_configure(cls):
        raise FailedToExecuteException("Cannot autoconfigure")

    def _inject_torrent(
        self,
        torrent_data,
        torrent_files,
        download_path,
        torrent_file_data=None,
        is_active=True,
    ):
        self._torrents[torrent_data.infohash] = TestTorrent(
            torrent_data, torrent_files, download_path, torrent_file_data, is_active
        )
