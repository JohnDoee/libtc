from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests
from requests.exceptions import RequestException

from ..baseclient import BaseClient
from ..bencode import bencode
from ..exceptions import FailedToExecuteException
from ..torrent import TorrentData, TorrentFile


def rewrite_path(path, path_mapping):
    for k, v in path_mapping.items():
        try:
            p = path.relative_to(k)
            return v / p
        except ValueError:
            pass
    return path


class LilTorrentClient(BaseClient):
    identifier = "liltorrent"
    display_name = "LilTorrent"

    def __init__(self, apikey, url, path_mapping=None):
        self.url = url
        self.apikey = apikey
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {apikey}",
        }
        if path_mapping:
            self.path_mapping = dict(
                [Path(p) for p in pm.split(":")] for pm in path_mapping.split(";")
            )
        else:
            self.path_mapping = {}

        self.reverse_path_mapping = {v: k for (k, v) in self.path_mapping.items()}

    def _call(self, _method, url, *args, **kwargs):
        url = urljoin(self.url, url)
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"].update(self.headers)
        try:
            r = getattr(requests, _method)(url, *args, **kwargs)
            if r.status_code == 500:
                raise FailedToExecuteException(*r.json())
            else:
                return r
        except RequestException:
            raise FailedToExecuteException("Unable to contact liltorrent instance")

    def _fetch_list_result(self, url):
        return [
            TorrentData.unserialize(torrent)
            for torrent in self._call("get", url).json()
        ]

    def list(self):
        return self._fetch_list_result("list")

    def list_active(self):
        return self._fetch_list_result("list_active")

    def start(self, infohash):
        return self._call("post", "start", params={"infohash": infohash}).json()

    def stop(self, infohash):
        return self._call("post", "stop", params={"infohash": infohash}).json()

    def test_connection(self):
        try:
            return self._call("get", "test_connection").json()
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
        destination_path = rewrite_path(destination_path, self.path_mapping)
        return self._call(
            "post",
            "add",
            params={
                "destination_path": str(destination_path),
                "fast_resume": fast_resume and "true" or "false",
                "add_name_to_folder": add_name_to_folder and "true" or "false",
                "minimum_expected_data": minimum_expected_data,
                "stopped": stopped and "true" or "false",
            },
            files={"torrent": bencode(torrent)},
        ).json()

    def remove(self, infohash):
        return self._call("post", "remove", params={"infohash": infohash}).json()

    def retrieve_torrentfile(self, infohash):
        return self._call(
            "get", "retrieve_torrentfile", params={"infohash": infohash}
        ).content

    def get_download_path(self, infohash):
        path = self._call(
            "get", "get_download_path", params={"infohash": infohash}
        ).json()
        return rewrite_path(Path(path), self.reverse_path_mapping)

    def get_files(self, infohash):
        return [
            TorrentFile.unserialize(torrent)
            for torrent in self._call(
                "get", "get_files", params={"infohash": infohash}
            ).json()
        ]

    def serialize_configuration(self):
        url = f"{self.identifier}+{self.url}"
        query = {}
        if self.apikey:
            query["apikey"] = str(self.apikey)

        if self.path_mapping:
            query["path_mapping"] = ";".join(
                [f"{k!s}:{v!s}" for (k, v) in self.path_mapping.items()]
            )

        if query:
            url += f"?{urlencode(query)}"

        return url

    @classmethod
    def auto_configure():
        raise FailedToExecuteException("Cannot auto-configure this type")

    def horse(self):
        return "horse"
