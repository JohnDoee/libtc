import logging

from datetime import datetime
from urllib.parse import urlsplit
from pathlib import Path
from xml.parsers.expat import ExpatError
from xmlrpc.client import Error as XMLRPCError
from xmlrpc.client import ServerProxy

import pytz

from ..exceptions import FailedToExecuteException
from ..scgitransport import SCGITransport
from ..torrent import TorrentData, TorrentState
from ..baseclient import BaseClient
from ..utils import map_existing_files
from ..bencode import bencode

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
            retval[piece//8] |= 1 << (7 - piece % 8)

    return bytes(retval)


class RTorrentClient(BaseClient):
    identifier = "rtorrent"
    _methods = None

    def __init__(self, url, session_path=None):
        self.proxy = create_proxy(url)
        self.session_path = Path(session_path)

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
                "d.directory=",
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

            progress = (torrent[6] / torrent[5]) * 100
            if torrent[11]:
                tracker = ".".join(torrent[11][0][0].split("/")[2].rsplit(".", 2)[1:])
            else:
                tracker = "None"

            result.append(
                TorrentData(
                    torrent[0].lower(),
                    torrent[1],
                    torrent[5],
                    state,
                    progress,
                    torrent[7],
                    datetime.utcfromtimestamp(torrent[10]).astimezone(pytz.UTC),
                    tracker,
                    torrent[8],
                    torrent[9],
                    torrent[12],
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

    def add(self, torrent, destination_path, fast_resume=False, add_name_to_folder=True, minimum_expected_data="none"):
        destination_path = destination_path.resolve()

        if fast_resume:
            logger.info('Adding fast resume data')

            psize = torrent[b'info'][b'piece length']
            pieces = len(torrent[b'info'][b'pieces']) // 20
            bitfield = [True] * pieces

            torrent[b'libtorrent_resume'] = {b'files': []}

            files = map_existing_files(torrent, destination_path)
            current_position = 0
            for fp, f, size, exists in files:
                logger.debug(f'Handling file {fp!r}')

                result = {b'priority': 1, b'completed': int(exists)}
                if exists:
                    result[b'mtime'] = int(fp.stat().st_mtime)
                torrent[b'libtorrent_resume'][b'files'].append(result)

                last_position = current_position + size

                first_piece = current_position // psize
                last_piece = (last_position + psize - 1) // psize

                for piece in range(first_piece, last_piece):
                    logger.debug(f'Setting piece {piece} to {exists}')
                    bitfield[piece] *= exists

                current_position = last_position

            if all(bitfield):
                logger.info('This torrent is complete, setting bitfield to chunk count')
                torrent[b'libtorrent_resume'][b'bitfield'] = pieces # rtorrent wants the number of pieces when torrent is complete
            else:
                logger.info('This torrent is incomplete, setting bitfield')
                torrent[b'libtorrent_resume'][b'bitfield'] = bitfield_to_string(bitfield)

        encoded_torrent = bencode(torrent)
        cmd = [encoded_torrent]
        if add_name_to_folder:
            cmd.append(f'd.directory.set="{destination_path!s}"')
        else:
            cmd.append(f'd.directory_base.set="{destination_path!s}"')
        logger.info(f"Sending to rtorrent: {cmd!r}")
        try:
            self.proxy.load.raw_start('', *cmd)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def remove(self, infohash):
        try:
            self.proxy.d.erase(infohash)
        except (XMLRPCError, ConnectionError, OSError, ExpatError):
            raise FailedToExecuteException()

    def retrieve_torrentfile(self, infohash):
        torrent_path = self.session_path / f"{infohash.upper()}.torrent"
        if not torrent_path.is_file():
            raise FailedToExecuteException()
        return torrent_path.read_bytes()