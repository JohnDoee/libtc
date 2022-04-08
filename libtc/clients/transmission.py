import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import pytz
import requests
from requests.exceptions import RequestException

from ..baseclient import BaseClient
from ..bencode import bencode
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentFile, TorrentState
from ..utils import (
    calculate_minimum_expected_data,
    get_tracker_domain,
    has_minimum_expected_data,
)

logger = logging.getLogger(__name__)


class TransmissionClient(BaseClient):
    identifier = "transmission"
    display_name = "Transmission"

    _session_id = ""

    def __init__(self, url, session_path=None, username=None, password=None):
        self.url = url
        self.session_path = session_path and Path(session_path)
        self.username = username
        self.password = password
        self.session = requests.Session()

    def _call(self, method, **kwargs):
        logger.debug(f"Calling {method!r} args {kwargs!r}")
        auth = None
        if self.username and self.password:
            auth = (self.username, self.password)
        return self.session.post(
            self.url,
            data=json.dumps({"method": method, "arguments": kwargs}),
            headers={"X-Transmission-Session-Id": self._session_id},
            auth=auth,
        )

    def call(self, method, **kwargs):
        try:
            r = self._call(method, **kwargs)
        except RequestException:
            raise FailedToExecuteException()
        if r.status_code == 409:
            self._session_id = r.headers["X-Transmission-Session-Id"]
            r = self._call(method, **kwargs)

        if r.status_code != 200:
            raise FailedToExecuteException()

        r = r.json()
        logger.debug("Got transmission reply")
        if r["result"] != "success":
            raise FailedToExecuteException()

        return r["arguments"]

    def _fetch_list_result(self, only_active):
        result = []
        fields = [
            "hashString",
            "name",
            "sizeWhenDone",
            "status",
            "error",
            "percentDone",
            "uploadedEver",
            "addedDate",
            "trackers",
            "rateUpload",
            "rateDownload",
        ]
        if only_active:
            call_result = self.call("torrent-get", ids="recently-active", fields=fields)
        else:
            call_result = self.call("torrent-get", fields=fields)
        for torrent in call_result["torrents"]:
            if torrent["error"] > 0:
                state = TorrentState.ERROR
            elif torrent["status"] > 0:
                state = TorrentState.ACTIVE
            else:
                state = TorrentState.STOPPED

            if torrent["trackers"]:
                tracker = get_tracker_domain(torrent["trackers"][0]["announce"])
            else:
                tracker = "None"

            result.append(
                TorrentData(
                    torrent["hashString"],
                    torrent["name"],
                    torrent["sizeWhenDone"],
                    state,
                    torrent["percentDone"] * 100,
                    torrent["uploadedEver"],
                    datetime.utcfromtimestamp(torrent["addedDate"]).astimezone(
                        pytz.UTC
                    ),
                    tracker,
                    torrent["rateUpload"],
                    torrent["rateDownload"],
                    "",
                )
            )
        return result

    def get_download_path(self, infohash):
        # It is impossible to determine the actual location of a file in transmission due to the
        # inability to determine if a torrent is a single-file or multi-file torrent without checking
        # This is best effort that will work in almost every case.
        call_result = self.call(
            "torrent-get", ids=[infohash], fields=["downloadDir", "name", "files"]
        )
        if not call_result["torrents"]:
            raise FailedToExecuteException("Torrent not found")

        torrent = call_result["torrents"][0]
        if len(torrent["files"]) == 1 and "/" not in torrent["files"][0]["name"]:
            return Path(torrent["downloadDir"])
        else:
            return (
                Path(torrent["downloadDir"]) / torrent["files"][0]["name"].split("/")[0]
            )

    def move_torrent(self, infohash, destination_path):
        call_result = self.call("torrent-get", ids=[infohash], fields=["name"])
        if not call_result["torrents"]:
            raise FailedToExecuteException("Torrent not found")

        self.call(
            "torrent-set-location",
            ids=[infohash],
            location=str(destination_path.resolve()),
            move=True,
        )

    def list(self):
        return self._fetch_list_result(False)

    def list_active(self):
        return self._fetch_list_result(True)

    def start(self, infohash):
        self.call("torrent-start", ids=[infohash])

    def stop(self, infohash):
        self.call("torrent-stop", ids=[infohash])

    def test_connection(self):
        try:
            session_data = self.call("session-get")
        except FailedToExecuteException:
            return False
        else:
            if session_data["rpc-version"] < 15:
                raise FailedToExecuteException(
                    "You need to update to a newer version of Transmission"
                )

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
        current_expected_data = calculate_minimum_expected_data(
            torrent, destination_path, add_name_to_folder
        )
        if not has_minimum_expected_data(minimum_expected_data, current_expected_data):
            raise FailedToExecuteException(
                f"Minimum expected data not reached, wanted {minimum_expected_data} actual {current_expected_data}"
            )
        if current_expected_data != "full":
            fast_resume = False
        destination_path = destination_path.resolve()
        encoded_torrent = base64.b64encode(bencode(torrent)).decode()

        name = torrent[b"info"][b"name"].decode()
        if add_name_to_folder:
            download_dir = destination_path
        else:
            if b"files" in torrent[b"info"]:
                download_dir = destination_path.parent
                display_name = destination_path.name
            else:
                download_dir = destination_path
                display_name = name

        kwargs = {
            "download-dir": str(download_dir),
            "metainfo": encoded_torrent,
            "paused": True,
        }
        result = self.call("torrent-add", **kwargs)
        tid = result["torrent-added"]["id"]

        if not add_name_to_folder:
            self.call(
                "torrent-rename-path", ids=[tid], path=str(name), name=str(display_name)
            )
            self.call("torrent-verify", ids=[tid])
        if not stopped:
            self.call("torrent-start", ids=[tid])

    def remove(self, infohash):
        self.call("torrent-remove", ids=[infohash])

    def retrieve_torrentfile(self, infohash):
        if not self.session_path:
            raise FailedToExecuteException("Session path is not configured")
        torrent_path = self.session_path / "torrents"
        for f in torrent_path.iterdir():
            if f.name.endswith(f".{infohash[:16]}.torrent"):
                return f.read_bytes()
        raise FailedToExecuteException("Torrent file does not exist")

    def get_files(self, infohash):
        call_result = self.call("torrent-get", ids=[infohash], fields=["name", "files"])
        torrent = call_result["torrents"][0]
        files = torrent["files"]
        is_singlefile = len(files) == 1 and "/" not in files[0]["name"]

        result = []
        for f in files:
            name = f["name"]
            if not is_singlefile:
                name = name.split("/", 1)[1]
            if f["length"] > 0:
                progress = (f["bytesCompleted"] / f["length"]) * 100
            else:
                progress = 100.0
            result.append(TorrentFile(name, f["length"], progress))

        return result

    def serialize_configuration(self):
        url = f"{self.identifier}+{self.url}"
        query = {}
        if self.session_path:
            query["session_path"] = str(self.session_path)

        if query:
            url += f"?{urlencode(query)}"

        return url

    @classmethod
    def auto_configure(cls, path="~/.config/transmission-daemon/settings.json"):
        config_path = Path(path).expanduser()
        if not config_path.is_file():
            raise FailedToExecuteException("Unable to find config file")

        try:
            config_data = json.loads(config_path.read_text())
        except PermissionError:
            raise FailedToExecuteException("Config file not accessible")

        ip = config_data.get("rpc-bind-address")
        port = config_data.get("rpc-port")
        if ip == "0.0.0.0":
            ip = "127.0.0.1"

        if not ip:
            raise FailedToExecuteException("Unable to find a bind ip")

        if not port:
            raise FailedToExecuteException("Unable to find port")

        return cls(
            f"http://{ip}:{port}/transmission/rpc", session_path=config_path.parent
        )
