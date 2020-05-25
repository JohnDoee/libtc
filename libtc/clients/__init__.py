from .deluge import DelugeClient
from .fakeclient import FakeClient
from .liltorrent import LilTorrentClient
from .qbittorrent import QBittorrentClient
from .rtorrent import RTorrentClient
from .transmission import TransmissionClient

TORRENT_CLIENT_MAPPING = {
    DelugeClient.identifier: DelugeClient,
    RTorrentClient.identifier: RTorrentClient,
    TransmissionClient.identifier: TransmissionClient,
    FakeClient.identifier: FakeClient,
    QBittorrentClient.identifier: QBittorrentClient,
    LilTorrentClient.identifier: LilTorrentClient,
}
