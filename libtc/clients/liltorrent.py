from urllib.parse import urljoin

import requests

from ..baseclient import BaseClient
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentState


class LilTorrentClient(BaseClient):
    identifier = "liltorrent"

    def __init__(self, username, password, url):
        self.url = url
        self.headers = {"Accept": "application/json"}
        self.auth = (username, password)

    def _call(self, _method, url, *args, **kwargs):
        url = urljoin(self.url, url)
        kwargs["auth"] = self.auth
        kwargs["headers"] = kwargs.get("headers", {}).update(self.headers)
        try:
            return getattr(requests, _method)(url, *args, **kwargs).json()
        except RequestException:
            raise FailedToExecuteException()

    def _fetch_list_result(self, url):
        return [TorrentData(**torrent) for torrent in self._call("get", url)]

    def list(self):
        return self._fetch_list_result("list")

    def list_active(self):
        return self._fetch_list_result("list_active")

    def start(self, infohash):
        return self._call("post", "start", params={"infohash": infohash})

    def stop(self, infohash):
        return self._call("post", "stop", params={"infohash": infohash})
