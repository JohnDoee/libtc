import base64
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import pytz
from deluge_client import DelugeRPCClient, LocalDelugeRPCClient
from deluge_client.client import DelugeClientException

from ..baseclient import BaseClient
from ..bencode import bencode
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentFile, TorrentState
from ..utils import (
    calculate_minimum_expected_data,
    has_minimum_expected_data,
    map_existing_files,
)


class DelugeClient(BaseClient):
    identifier = "deluge"
    display_name = "Deluge"

    keys = [
        "name",
        "progress",
        "state",
        "total_size",
        "time_added",
        "total_uploaded",
        "tracker_host",
        "upload_payload_rate",
        "download_payload_rate",
        "label",
    ]

    def __init__(self, host, port, username, password, session_path=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.session_path = session_path and Path(session_path)

    @property
    def client(self):
        return DelugeRPCClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            decode_utf8=True,
        )

    def _fetch_list_result(self, filter):
        result = []
        try:
            with self.client as client:
                torrents = client.core.get_torrents_status(filter, self.keys)
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException()
        for infohash, torrent_data in torrents.items():
            if torrent_data["state"] in ["Seeding", "Downloading"]:
                state = TorrentState.ACTIVE
            elif torrent_data["state"] in ["Error"]:
                state = TorrentState.ERROR
            else:
                state = TorrentState.STOPPED

            result.append(
                TorrentData(
                    infohash,
                    torrent_data["name"],
                    torrent_data["total_size"],
                    state,
                    torrent_data["progress"],
                    torrent_data["total_uploaded"],
                    datetime.utcfromtimestamp(torrent_data["time_added"]).astimezone(
                        pytz.UTC
                    ),
                    torrent_data["tracker_host"],
                    torrent_data["upload_payload_rate"],
                    torrent_data["download_payload_rate"],
                    torrent_data.get("label", ""),
                )
            )
        return result

    def list(self):
        return self._fetch_list_result({})

    def list_active(self):
        return self._fetch_list_result({"state": "Active"})

    def start(self, infohash):
        try:
            with self.client as client:
                client.core.resume_torrent([infohash])
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException()

    def stop(self, infohash):
        try:
            with self.client as client:
                client.core.pause_torrent([infohash])
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException()

    def test_connection(self):
        try:
            with self.client as client:
                return client.core.get_free_space() is not None
        except (DelugeClientException, ConnectionError, OSError):
            return False

    def add(
        self,
        torrent,
        destination_path,
        fast_resume=False,
        add_name_to_folder=True,
        minimum_expected_data="none",
        stopped=False,
    ):
        current_expected_data = calculate_minimum_expected_data(
            torrent, destination_path, add_name_to_folder
        )
        if not has_minimum_expected_data(minimum_expected_data, current_expected_data):
            raise FailedToExecuteException(
                f"Minimum expected data not reached, wanted {minimum_expected_data} actual {current_expected_data}"
            )
        destination_path = destination_path.resolve()
        encoded_torrent = base64.b64encode(bencode(torrent))
        infohash = hashlib.sha1(bencode(torrent[b"info"])).hexdigest()
        options = {"download_location": str(destination_path), "seed_mode": fast_resume}
        if stopped:
            options["add_paused"] = True
        if not add_name_to_folder:
            files = map_existing_files(
                torrent, destination_path, add_name_to_folder=False
            )
            mapped_files = {}
            for i, (fp, f, size, exists) in enumerate(files):
                mapped_files[i] = str(f)
            options["mapped_files"] = mapped_files

        try:
            with self.client as client:
                result = client.core.add_torrent_file(
                    "torrent.torrent", encoded_torrent, options
                )
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException()

        if result != infohash:
            raise FailedToExecuteException()

    def remove(self, infohash):
        try:
            with self.client as client:
                client.core.remove_torrent(infohash, False)
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException()

    def retrieve_torrentfile(self, infohash):
        if not self.session_path:
            raise FailedToExecuteException("Session path is not configured")
        torrent_path = self.session_path / "state" / f"{infohash}.torrent"
        if not torrent_path.is_file():
            raise FailedToExecuteException("Torrent file does not exist")
        return torrent_path.read_bytes()

    def get_download_path(self, infohash):
        # Deluge has a download place and an internal mapping relative to the files
        # which makes it a bit of a guesswork to figure out the download folder.
        # The algorithm we will be using is, multifile and a single shared prefix (also single folder max).
        try:
            with self.client as client:
                torrents = client.core.get_torrents_status(
                    {"id": [infohash]},
                    ["name", "download_location", "save_path", "files"],
                )
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException(
                "Failed to fetch download_location from Deluge"
            )

        if not torrents:
            raise FailedToExecuteException("Empty result from deluge")

        torrent_data = torrents[infohash]
        download_location = torrent_data.get(
            "download_location", torrent_data.get("save_path")
        )
        if not download_location:
            raise FailedToExecuteException(
                "Unable to retrieve a valid download_location"
            )
        if (
            len(torrent_data["files"]) == 1
            and "/" not in torrent_data["files"][0]["path"]
        ):
            return Path(download_location)

        prefixes = set(f["path"].split("/")[0] for f in torrent_data["files"])
        if len(prefixes) == 1:
            return Path(download_location) / list(prefixes)[0]
        else:
            return Path(download_location)

    def get_files(self, infohash):
        try:
            with self.client as client:
                torrents = client.core.get_torrents_status(
                    {"id": [infohash]}, ["name", "files", "file_progress"],
                )
        except (DelugeClientException, ConnectionError, OSError):
            raise FailedToExecuteException("Failed to fetch files from Deluge")

        torrent_data = torrents[infohash]
        files = torrent_data["files"]
        file_progress = torrent_data["file_progress"]
        is_singlefile = len(files) == 1 and "/" not in files[0]["path"]
        result = []
        for f, p in zip(files, file_progress):
            name = f["path"]
            if not is_singlefile:
                name = name.split("/", 1)[1]
            result.append(TorrentFile(name, f["size"], p * 100))
        return result

    def serialize_configuration(self):
        url = f"{self.identifier}://{self.username}:{self.password}@{self.host}:{self.port}"
        query = {}
        if self.session_path:
            query["session_path"] = str(self.session_path)

        if query:
            url += f"?{urlencode(query)}"

        return url

    @classmethod
    def auto_configure(cls):
        client = LocalDelugeRPCClient()
        return cls(client.host, client.port, client.username, client.password)
