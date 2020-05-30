import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.exceptions import RequestException

from ..baseclient import BaseClient
from ..bencode import bencode
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentState
from ..utils import calculate_minimum_expected_data, has_minimum_expected_data


class QBittorrentClient(BaseClient):
    identifier = "qbittorrent"

    def __init__(self, url, username, password, session_path=None):
        self.url = url
        self.username = username
        self.password = password
        self.session_path = session_path and Path(session_path)
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
                tracker = ".".join(torrent["tracker"].split("/")[2].rsplit(".", 2)[1:])

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
    ):
        current_expected_data = calculate_minimum_expected_data(
            torrent, destination_path, add_name_to_folder
        )
        if not has_minimum_expected_data(minimum_expected_data, current_expected_data):
            raise FailedToExecuteException(
                f"Minimum expected data not reached, wanted {minimum_expected_data} actual {current_expected_data}"
            )
        create_subfolder_enabled = self.call("get", "/api/v2/app/preferences").json()[
            "create_subfolder_enabled"
        ]
        changed_create_subfolder_enabled = False
        encoded_torrent = bencode(torrent)
        data = {
            "savepath": str(destination_path),
            "skip_checking": (fast_resume and "true" or "false"),
        }

        name = torrent[b"info"][b"name"].decode()
        if b"files" in torrent[b"info"]:
            if create_subfolder_enabled and not add_name_to_folder:
                self.call(
                    "post",
                    "/api/v2/app/setPreferences",
                    data={"json": json.dumps({"create_subfolder_enabled": False})},
                )
                changed_create_subfolder_enabled = True
            elif not create_subfolder_enabled and add_name_to_folder:
                data["savepath"] = destination_path / name
        self.call(
            "post",
            "/api/v2/torrents/add",
            files={"torrents": encoded_torrent},
            data=data,
        )
        if changed_create_subfolder_enabled:
            self.call(
                "post",
                "/api/v2/app/setPreferences",
                data={"json": json.dumps({"create_subfolder_enabled": True})},
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
        if not torrent_path.is_file():
            raise FailedToExecuteException("Torrent file does not exist")
        return torrent_path.read_bytes()

    def get_download_path(self, infohash):
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
            return Path(torrent["save_path"])

        prefixes = set(f["name"].split("/")[0] for f in torrent_files)
        if len(prefixes) and list(prefixes)[0] == torrent["name"]:
            return Path(torrent["save_path"]) / torrent["name"]
        else:
            return Path(torrent["save_path"])
