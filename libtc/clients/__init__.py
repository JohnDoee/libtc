from .deluge import DelugeClient
from .rtorrent import RTorrentClient
from .transmission import TransmissionClient
from .fakeclient import FakeClient
from .qbittorrent import QBittorrentClient
from .liltorrent import LilTorrentClient

TORRENT_CLIENT_MAPPING = {
    DelugeClient.identifier: DelugeClient,
    RTorrentClient.identifier: RTorrentClient,
    TransmissionClient.identifier: TransmissionClient,
    FakeClient.identifier: FakeClient,
    QBittorrentClient.identifier: QBittorrentClient,
    LilTorrentClient.identifier: LilTorrentClient,
}