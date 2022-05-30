import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit, quote
from xml.parsers.expat import ExpatError
from xmlrpc.client import Error as XMLRPCError
from xmlrpc.client import ServerProxy

import pytz

from ..baseclient import BaseClient
from ..bencode import bencode
from ..exceptions import FailedToExecuteException
from ..scgitransport import SCGITransport
from ..torrent import TorrentData, TorrentFile, TorrentState
from ..utils import (
    calculate_minimum_expected_data,
    get_tracker_domain,
    has_minimum_expected_data,
    map_existing_files,
    move_files,
)

logger = logging.getLogger(__name__)


def create_proxy(url):
    parsed = urlsplit(url)
    proto = url.split(":")[0].lower()
    if proto == "scgi":
        if parsed.netloc:
            url = f"http://{parsed.netloc}"
            logger.debug(f"Creating SCGI XMLRPC Proxy with url {url}")
            return ServerProxy(url, transport=SCGITransport())
        else:
            path = parsed.path
            logger.debug(f"Creating SCGI XMLRPC Socket Proxy with socket file {path}")
            return ServerProxy("http://1", transport=SCGITransport(socket_path=path))
    else:
        logger.debug(f"Creating Normal XMLRPC Proxy with url {url}")
        return ServerProxy(url)


def bitfield_to_string(bitfield):
    """
    Converts a list of booleans into a bitfield
    """
    retval = bytearray((len(bitfield) + 7) // 8)

    for piece, bit in enumerate(bitfield):
        if bit:
            retval[piece // 8] |= 1 << (7 - piece % 8)

    return bytes(retval)


class RTorrentClient(BaseClient):
    identifier = "rtorrent"
    display_name = "rtorrent"
    _methods = None

    def __init__(self, url, session_path=None, torrent_temp_path=None, label=None):
        self.url = url
        self.proxy = create_proxy(url)
        self.session_path = session_path and Path(session_path)
        self.torrent_temp_path = torrent_temp_path and Path(torrent_temp_path)
        self.label = label

    def _fetch_list_result(self, view):
        result = []
        try:
            torrents = self.proxy.d.multicall2(
                "",
                view,
                "d.hash=",
                "d.name=",
                "d.is_active=",
                "d.message=",
                "d.size_bytes=",
                "d.completed_bytes=",
                "d.up.total=",
                "d.up.rate=",
                "d.down.rate=",
                "d.timestamp.finished=",
                "t.multicall=,t.url=",
                "d.custom1=",
            )
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()
        for torrent in torrents:
            if torrent[3]:
                state = TorrentState.ERROR
            elif torrent[2] == 0:
                state = TorrentState.STOPPED
            else:
                state = TorrentState.ACTIVE

            progress = (torrent[5] / torrent[4]) * 100
            if torrent[10]:
                tracker = get_tracker_domain(torrent[10][0][0])
            else:
                tracker = "None"

            result.append(
                TorrentData(
                    torrent[0].lower(),
                    torrent[1],
                    torrent[4],
                    state,
                    progress,
                    torrent[6],
                    datetime.utcfromtimestamp(torrent[9]).astimezone(pytz.UTC),
                    tracker,
                    torrent[7],
                    torrent[8],
                    torrent[11],
                )
            )

        return result

    def get_methods(self):
        if self._methods is None:
            self._methods = self.proxy.system.listMethods()

        return self._methods

    def list(self):
        return self._fetch_list_result("main")

    def list_active(self):
        try:
            if "spreadsheet_active" not in self.proxy.view.list():
                self.proxy.view.add("", "spreadsheet_active")
            self.proxy.view.filter(
                "", "spreadsheet_active", "or={d.up.rate=,d.down.rate=}"
            )
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()
        return self._fetch_list_result("spreadsheet_active")

    def start(self, infohash):
        try:
            self.proxy.d.start(infohash)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def stop(self, infohash):
        try:
            self.proxy.d.stop(infohash)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def test_connection(self):
        try:
            return self.proxy.system.pid() is not None
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
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

        if fast_resume:
            logger.info("Adding fast resume data")

            psize = torrent[b"info"][b"piece length"]
            pieces = len(torrent[b"info"][b"pieces"]) // 20
            bitfield = [True] * pieces

            torrent[b"libtorrent_resume"] = {b"files": []}

            files = map_existing_files(torrent, destination_path)
            current_position = 0
            for fp, f, size, exists in files:
                logger.debug(f"Handling file {fp!r}")

                result = {b"priority": 1, b"completed": int(exists)}
                if exists:
                    result[b"mtime"] = int(fp.stat().st_mtime)
                torrent[b"libtorrent_resume"][b"files"].append(result)

                last_position = current_position + size

                first_piece = current_position // psize
                last_piece = (last_position + psize - 1) // psize

                for piece in range(first_piece, last_piece):
                    logger.debug(f"Setting piece {piece} to {exists}")
                    bitfield[piece] *= exists

                current_position = last_position

            if all(bitfield):
                logger.info("This torrent is complete, setting bitfield to chunk count")
                torrent[b"libtorrent_resume"][
                    b"bitfield"
                ] = pieces  # rtorrent wants the number of pieces when torrent is complete
            else:
                logger.info("This torrent is incomplete, setting bitfield")
                torrent[b"libtorrent_resume"][b"bitfield"] = bitfield_to_string(
                    bitfield
                )

        encoded_torrent = bencode(torrent)
        cmd = [encoded_torrent]
        if add_name_to_folder:
            cmd.append(f'd.directory.set="{destination_path!s}"')
        else:
            cmd.append(f'd.directory_base.set="{destination_path!s}"')
        if self.label:
            cmd.append(f'd.custom1.set={quote(self.label)}')
        logger.info(f"Sending to rtorrent: {cmd!r}")
        try:  # TODO: use torrent_temp_path if payload is too big
            if stopped:
                self.proxy.load.raw("", *cmd)
            else:
                self.proxy.load.raw_start("", *cmd)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def remove(self, infohash):
        try:
            self.proxy.d.erase(infohash)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def retrieve_torrentfile(self, infohash):
        if not self.session_path:
            raise FailedToExecuteException("Session path is not configured")
        torrent_path = self.session_path / f"{infohash.upper()}.torrent"
        if not torrent_path.is_file():
            raise FailedToExecuteException("Torrent file does not exist")
        return torrent_path.read_bytes()

    def get_download_path(self, infohash):
        try:
            return Path(self.proxy.d.directory(infohash))
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException("Failed to retrieve download path")

    def move_torrent(self, infohash, destination_path):
        files = self.get_files(infohash)
        current_download_path = self.get_download_path(infohash)
        is_multi_file = self.proxy.d.is_multi_file(infohash)

        self.stop(infohash)
        self.proxy.d.directory.set(infohash, str(destination_path))
        if is_multi_file:
            move_files(
                current_download_path,
                destination_path / current_download_path.name,
                files,
            )
        else:
            move_files(
                current_download_path,
                destination_path,
                files,
                preserve_parent_folder=True,
            )

        self.start(infohash)

    def get_files(self, infohash):
        result = []
        try:
            files = self.proxy.f.multicall(
                infohash,
                "",
                "f.path=",
                "f.size_bytes=",
                "f.completed_chunks=",
                "f.size_chunks=",
            )
            for f in files:
                path, size, completed_chunks, size_chunks = f
                if completed_chunks > size_chunks:
                    completed_chunks = size_chunks

                if size_chunks == 0:
                    progress = 0.0
                else:
                    progress = (completed_chunks / size_chunks) * 100
                result.append(TorrentFile(path, size, progress))
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException("Failed to retrieve files")

        return result

    def serialize_configuration(self):
        url = f"{self.identifier}+{self.url}"
        query = {}
        if self.session_path:
            query["session_path"] = str(self.session_path)

        if self.label:
            query["label"] = self.label

        if query:
            url += f"?{urlencode(query)}"

        return url

    @classmethod
    def auto_configure(cls, path="~/.rtorrent.rc"):
        # Does not work with latest rtorrent config
        config_path = Path(path).expanduser()
        if not config_path.is_file():
            raise FailedToExecuteException("Unable to find config file")

        try:
            config_data = config_path.read_text()
        except PermissionError:
            raise FailedToExecuteException("Config file not accessible")

        scgi_info = re.findall(
            r"^\s*scgi_(port|local)\s*=\s*(.+)\s*$", str(config_data), re.MULTILINE
        )
        if not scgi_info:
            raise FailedToExecuteException("No scgi info found in configuration file")

        scgi_method, scgi_url = scgi_info[0]

        if scgi_method == "port":
            scgi_url = scgi_url.strip()
        else:
            scgi_url = Path(scgi_url.strip()).expanduser().resolve()

        client = cls(f"scgi://{scgi_url}")
        session_path = Path(client.proxy.session.path()).resolve()
        if session_path.is_dir():
            client.session_path = session_path
        return client
