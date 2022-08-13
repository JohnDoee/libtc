import json
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

import requests
from requests.exceptions import RequestException

from ..baseclient import BaseClient
from ..bencode import bdecode, bencode
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentFile, TorrentState
from ..utils import (
    calculate_minimum_expected_data,
    get_tracker_domain,
    has_minimum_expected_data,
    move_files,
)


class QBittorrentClient(BaseClient):
    identifier = "qbittorrent"
    display_name = "qBittorrent"

    def __init__(self, url, username, password, session_path=None, label=None):
        self.url = url
        self.username = username
        self.password = password
        self.session_path = session_path and Path(session_path)
        self.label = label
        self._session = requests.Session()

    def _call(self, _method, url, *args, **kwargs):
        return getattr(self._session, _method)(urljoin(self.url, url), *args, **kwargs)

    def _login(self):
        r = self._call(
            "post",
            urljoin(self.url, "/api/v2/auth/login"),
            headers={"Referer": self.url},
            data={"username": self.username, "password": self.password},
        )

        return r.status_code == 200

    def call(self, method, url, *args, **kwargs):
        try:
            r = self._call(method, url, *args, **kwargs)
        except RequestException:
            raise FailedToExecuteException()

        if r.status_code > 400:
            if not self._login():
                raise FailedToExecuteException()

            r = self._call(method, url, *args, **kwargs)

            if r.status_code > 400:
                raise FailedToExecuteException()

        return r

    def _fetch_list_result(self, filter):
        result = []
        torrents = self.call(
            "get", "/api/v2/torrents/info", params={"filter": filter}
        ).json()
        for torrent in torrents:
            if torrent["state"] == "error":
                state = TorrentState.ERROR
            if torrent["state"].startswith("paused") or torrent["state"].startswith(
                "queued"
            ):
                state = TorrentState.STOPPED
            else:
                state = TorrentState.ACTIVE

            tracker = ""
            if torrent["tracker"]:
                tracker = get_tracker_domain(torrent["tracker"])

            result.append(
                TorrentData(
                    torrent["hash"],
                    torrent["name"],
                    torrent["size"],
                    state,
                    torrent["progress"] * 100.0,
                    torrent["uploaded"],
                    torrent["added_on"],
                    tracker,
                    torrent["upspeed"],
                    torrent["dlspeed"],
                    torrent["category"],
                )
            )

        return result

    def list(self):
        return self._fetch_list_result("all")

    def list_active(self):
        return self._fetch_list_result("active")

    def start(self, infohash):
        self.call("get", "/api/v2/torrents/resume", params={"hashes": infohash})

    def stop(self, infohash):
        self.call("get", "/api/v2/torrents/pause", params={"hashes": infohash})

    def test_connection(self):
        try:
            return len(self.call("get", "/api/v2/app/version").text) > 0
        except FailedToExecuteException:
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
        encoded_torrent = bencode(torrent)
        data = {
            "savepath": str(destination_path),
            "skip_checking": (fast_resume and "true" or "false"),
            "autoTMM": "false",
            "root_folder": add_name_to_folder,
            "contentLayout": (add_name_to_folder and "Original" or "NoSubfolder"),
        }
        if stopped:
            data["paused"] = "true"
        if self.label:
            data["tags"] = self.label

        self.call(
            "post",
            "/api/v2/torrents/add",
            files={"torrents": encoded_torrent},
            data=data,
        )

    def remove(self, infohash):
        self.call(
            "get",
            "/api/v2/torrents/delete",
            params={"hashes": infohash, "deleteFiles": "false"},
        )

    def retrieve_torrentfile(self, infohash):
        if not self.session_path:
            raise FailedToExecuteException("Session path is not configured")
        torrent_path = self.session_path / "data" / "BT_backup" / f"{infohash}.torrent"
        torrent_resume_path = (
            self.session_path / "data" / "BT_backup" / f"{infohash}.fastresume"
        )

        if not torrent_path.is_file():
            raise FailedToExecuteException("Torrent file does not exist")
        torrent_data = bdecode(torrent_path.read_bytes())
        if b"announce" not in torrent_data:
            if not torrent_resume_path.is_file():
                raise FailedToExecuteException("Torrent resume file does not exist")
            torrent_resume_data = bdecode(torrent_resume_path.read_bytes())
            trackers = torrent_resume_data.get(b"trackers")
            if not trackers:
                raise FailedToExecuteException("No trackers found in torrent file")
            torrent_data[b"announce"] = trackers.pop(0)[0]
            if trackers:
                torrent_data[b"announce-list"] = trackers

        return bencode(torrent_data)

    def get_download_path(self, infohash):
        return self._get_download_path(infohash)[0]

    def _get_download_path(self, infohash):
        torrents = self.call(
            "get", "/api/v2/torrents/info", params={"hashes": infohash}
        ).json()
        torrent_files = self.call(
            "get", "/api/v2/torrents/files", params={"hash": infohash}
        ).json()
        if not torrents or not torrent_files:
            raise FailedToExecuteException("Failed to retrieve download path")

        torrent = torrents[0]

        if len(torrent_files) == 1 and torrent_files[0]["name"] == torrent["name"]:
            return Path(torrent["save_path"]), False

        prefixes = set(f["name"].split("/")[0] for f in torrent_files)
        if len(prefixes) == 1 and list(prefixes)[0] == torrent["name"]:
            return Path(torrent["save_path"]) / torrent["name"], True
        elif len(prefixes) > 1:
            return Path(torrent["save_path"]), True
        else:
            return Path(torrent["save_path"]), False

    def move_torrent(self, infohash, destination_path):
        self.stop(infohash)
        current_download_path, contains_folder_name = self._get_download_path(infohash)
        files = self.get_files(infohash)

        move_files(current_download_path, destination_path, files)
        if contains_folder_name:
            current_download_path = current_download_path.parent
        self.call(
            "post",
            "/api/v2/torrents/setLocation",
            data={"hashes": infohash, "location": str(destination_path)},
        )
        for _ in range(20):
            import time

            time.sleep(0.3)
            print(self._get_download_path(infohash))
        self.start(infohash)

    def get_files(self, infohash):
        torrents = self.call(
            "get", "/api/v2/torrents/info", params={"hashes": infohash}
        ).json()
        torrent_files = self.call(
            "get", "/api/v2/torrents/files", params={"hash": infohash}
        ).json()
        torrent = torrents[0]
        prefixes = set(f["name"].split("/")[0] for f in torrent_files)
        trim_prefix = len(prefixes) == 1 and list(prefixes)[0] == torrent["name"]
        result = []
        for f in torrent_files:
            if trim_prefix and "/" in f["name"]:
                name = f["name"].split("/", 1)[1]
            else:
                name = f["name"]
            result.append(
                TorrentFile(
                    name,
                    f["size"],
                    f["progress"] * 100,
                )
            )
        return result

    def serialize_configuration(self):
        parsed = urlparse(self.url)
        url = f"{self.identifier}+{parsed.scheme}://{self.username}:{self.password}@{parsed.netloc}{parsed.path}"
        query = {}
        if self.session_path:
            query["session_path"] = str(self.session_path)

        if query:
            url += f"?{urlencode(query)}"

        return url

    @classmethod
    def auto_configure(cls):
        raise FailedToExecuteException("Unable to auto configure this client type")
