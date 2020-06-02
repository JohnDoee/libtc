from urllib.parse import parse_qsl, urlparse

from .deluge import DelugeClient
from .fakeclient import FakeClient
from .liltorrent import LilTorrentClient
from .qbittorrent import QBittorrentClient
from .rtorrent import RTorrentClient
from .transmission import TransmissionClient

__all__ = [
    "DelugeClient",
    "FakeClient","LilTorrentClient", "QBittorrentClient","RTorrentClient","TransmissionClient","TORRENT_CLIENT_MAPPING","parse_libtc_url"
]

TORRENT_CLIENT_MAPPING = {
    DelugeClient.identifier: DelugeClient,
    RTorrentClient.identifier: RTorrentClient,
    TransmissionClient.identifier: TransmissionClient,
    FakeClient.identifier: FakeClient,
    QBittorrentClient.identifier: QBittorrentClient,
    LilTorrentClient.identifier: LilTorrentClient,
}


def parse_libtc_url(url):
    # transmission+http://127.0.0.1:9091/?session_path=/session/path/
    # rtorrent+scgi:///path/to/socket.scgi?session_path=/session/path/
    # deluge://username:password@127.0.0.1:58664/?session_path=/session/path/
    # qbittorrent+http://username:password@127.0.0.1:8080/?session_path=/session/path/

    if url in TORRENT_CLIENT_MAPPING:
        return TORRENT_CLIENT_MAPPING[url].auto_config()

    kwargs = {}
    parsed = urlparse(url)
    scheme = parsed.scheme.split("+")
    netloc = parsed.netloc
    if "@" in netloc:
        auth, netloc = netloc.split("@")
        username, password = auth.split(":")
        kwargs["username"] = username
        kwargs["password"] = password

    client = scheme[0]
    if len(scheme) == 2:
        kwargs["url"] = f"{scheme[1]}://{netloc}{parsed.path}"
    else:
        kwargs["host"], kwargs["port"] = netloc.split(":")
        kwargs["port"] = int(kwargs["port"])

    kwargs.update(dict(parse_qsl(parsed.query)))
    return TORRENT_CLIENT_MAPPING[client](**kwargs)
