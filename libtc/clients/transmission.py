import base64
import json
import logging
from datetime import datetime
from pathlib import Path

import pytz
import requests
from requests.exceptions import RequestException

from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentState
from ..baseclient import BaseClient
from ..bencode import bencode

logger = logging.getLogger(__name__)


class TransmissionClient(BaseClient):
    identifier = 'transmission'

    _session_id = ""

    def __init__(self, url, session_path=None):
        self.url = url
        self.session_path = Path(session_path)

    def _call(self, method, **kwargs):
        logger.debug(f"Calling {method!r} args {kwargs!r}")
        return requests.post(
            self.url,
            data=json.dumps({"method": method, "arguments": kwargs}),
            headers={"X-Transmission-Session-Id": self._session_id},
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
                tracker = ".".join(
                    torrent["trackers"][0]["announce"].split("/")[2].rsplit(".", 2)[1:]
                )
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
                raise FailedToExecuteException("You need to update to a newer version of Transmission")

            return True

    def add(self, torrent, destination_path, fast_resume=False, add_name_to_folder=True, minimum_expected_data="none"):
        destination_path = destination_path.resolve()
        encoded_torrent = base64.b64encode(bencode(torrent)).decode()

        name = torrent[b'info'][b'name'].decode()
        if add_name_to_folder:
            download_dir = str(destination_path)
        else:
            if b'files' in torrent[b'info']:
                download_dir = destination_path.parent
                display_name = destination_path.name
            else:
                download_dir = destination_path
                display_name = name

        kwargs = {'download-dir': str(download_dir), 'metainfo': encoded_torrent, 'paused': True}
        result = self.call('torrent-add', **kwargs)
        tid = result['torrent-added']['id']

        if not add_name_to_folder:
            self.call('torrent-rename-path', ids=[tid], path=str(name), name=str(display_name))
        self.call('torrent-start', ids=[tid])

    def remove(self, infohash):
        self.call('torrent-remove', ids=[infohash])

    def retrieve_torrentfile(self, infohash):
        torrent_path = self.session_path / "torrents"
        for f in torrent_path.iterdir():
            if f.name.endswith(f".{infohash[:16]}.torrent"):
                return f.read_bytes()
        raise FailedToExecuteException()
