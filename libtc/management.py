import logging

from .bencode import BTFailure, bdecode
from .exceptions import FailedToExecuteException
from .torrent import TorrentState

logger = logging.getLogger(__name__)


def move_torrent(
    infohash, source_client, target_client, fast_resume=False
):  # TODO: preserver start/stop
    source_client.test_connection()
    target_client.test_connection()

    source_torrents = source_client.list()
    source_torrent = [t for t in source_torrents if t.infohash == infohash]
    if not source_torrent:
        raise FailedToExecuteException(f"Infohash {infohash} was not found on source")
    source_torrent = source_torrent[0]

    target_torrents = target_client.list()
    if any(t for t in target_torrents if t.infohash == infohash):
        raise FailedToExecuteException(f"Infohash {infohash} was found on target")

    if source_torrent.state == TorrentState.ERROR:
        raise FailedToExecuteException("Cannot move a torrent in an error state")

    try:
        torrent_data = bdecode(source_client.retrieve_torrentfile(infohash))
    except BTFailure:
        raise FailedToExecuteException("Unable to decode retrieved torrent")

    # if multifile and path ends with 'name', add without skip_name, otherwise add with name and path trimmed
    download_path = source_client.get_download_path(infohash)
    if (
        b"files" in torrent_data[b"info"]
        and download_path.name == torrent_data[b"info"][b"name"].decode()
    ):
        download_path = download_path.parent
        add_name_to_folder = True
    else:
        add_name_to_folder = False

    if source_torrent.state == TorrentState.ACTIVE:
        source_client.stop(infohash)
    try:
        target_client.add(
            torrent_data,
            download_path,
            fast_resume=fast_resume,
            add_name_to_folder=add_name_to_folder,
            minimum_expected_data="full",
            stopped=source_torrent.state == TorrentState.STOPPED,
        )
    except FailedToExecuteException:
        logger.exception("Failed to add torrent to the new client")
        if source_torrent.state == TorrentState.ACTIVE:
            source_client.start(infohash)
        raise FailedToExecuteException("Failed to add torrent to new client")

    source_client.remove(infohash)
