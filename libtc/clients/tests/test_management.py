import hashlib
import time
from pathlib import Path

import pytest

from libtc import TorrentState, bdecode, bencode, move_torrent

from .basetest import testfiles, verify_torrent_state
from .test_deluge import client as deluge_client
from .test_qbittorrent import client as qbittorrent_client
from .test_rtorrent import client as rtorrent_client
from .test_transmission import client as transmission_client


@pytest.mark.parametrize(
    "source_client_name,target_client_name",
    [
        ("deluge", "qbittorrent"),
        ("qbittorrent", "rtorrent"),
        ("rtorrent", "transmission"),
        ("transmission", "deluge"),
    ],
)
def test_move_multifile(
    source_client_name,
    target_client_name,
    testfiles,
    deluge_client,
    qbittorrent_client,
    rtorrent_client,
    transmission_client,
):
    clients = {
        "deluge": deluge_client,
        "qbittorrent": qbittorrent_client,
        "rtorrent": rtorrent_client,
        "transmission": transmission_client,
    }

    source_client = clients[source_client_name]
    target_client = clients[target_client_name]

    torrent = testfiles / "Some-Release.torrent"
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b"info"])).hexdigest()
    source_client.add(torrent_data, testfiles, fast_resume=False)

    verify_torrent_state(
        source_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    move_torrent(infohash, source_client, target_client)
    verify_torrent_state(
        target_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    verify_torrent_state(
        source_client,
        [],
    )
    target_client.remove(infohash)
    verify_torrent_state(
        target_client,
        [],
    )


@pytest.mark.parametrize(
    "source_client_name,target_client_name",
    [
        ("deluge", "qbittorrent"),
        ("qbittorrent", "rtorrent"),
        ("rtorrent", "transmission"),
        ("transmission", "deluge"),
    ],
)
def test_move_singlefile(
    source_client_name,
    target_client_name,
    testfiles,
    deluge_client,
    qbittorrent_client,
    rtorrent_client,
    transmission_client,
):
    clients = {
        "deluge": deluge_client,
        "qbittorrent": qbittorrent_client,
        "rtorrent": rtorrent_client,
        "transmission": transmission_client,
    }

    source_client = clients[source_client_name]
    target_client = clients[target_client_name]

    torrent = testfiles / "test_single.torrent"
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b"info"])).hexdigest()
    source_client.add(torrent_data, testfiles, fast_resume=False)

    verify_torrent_state(
        source_client,
        [
            {
                "infohash": infohash,
                "name": "file_a.txt",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    move_torrent(infohash, source_client, target_client)
    verify_torrent_state(
        target_client,
        [
            {
                "infohash": infohash,
                "name": "file_a.txt",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    verify_torrent_state(
        source_client,
        [],
    )
    target_client.remove(infohash)
    verify_torrent_state(
        target_client,
        [],
    )


@pytest.mark.parametrize(
    "source_client_name,target_client_name",
    [
        ("deluge", "qbittorrent"),
        ("qbittorrent", "rtorrent"),
        ("rtorrent", "transmission"),
        ("transmission", "deluge"),
    ],
)
def test_move_multifile_no_add_name_to_folder(
    source_client_name,
    target_client_name,
    testfiles,
    deluge_client,
    qbittorrent_client,
    rtorrent_client,
    transmission_client,
):
    clients = {
        "deluge": deluge_client,
        "qbittorrent": qbittorrent_client,
        "rtorrent": rtorrent_client,
        "transmission": transmission_client,
    }

    source_client = clients[source_client_name]
    target_client = clients[target_client_name]

    new_path = Path(testfiles) / "New-Some-Release"
    (testfiles / "Some-Release").rename(new_path)
    torrent = testfiles / "Some-Release.torrent"
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b"info"])).hexdigest()
    source_client.add(
        torrent_data,
        new_path,
        fast_resume=False,
        add_name_to_folder=False,
        minimum_expected_data="full",
    )

    verify_torrent_state(
        source_client,
        [
            {
                "infohash": infohash,
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    move_torrent(infohash, source_client, target_client)
    verify_torrent_state(
        target_client,
        [
            {
                "infohash": infohash,
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    verify_torrent_state(
        source_client,
        [],
    )
    target_client.remove(infohash)
    verify_torrent_state(
        target_client,
        [],
    )


@pytest.mark.parametrize(
    "source_client_name,target_client_name",
    [
        ("deluge", "qbittorrent"),
        ("qbittorrent", "rtorrent"),
        ("rtorrent", "transmission"),
        ("transmission", "deluge"),
    ],
)
def test_move_multifile_stopped(
    source_client_name,
    target_client_name,
    testfiles,
    deluge_client,
    qbittorrent_client,
    rtorrent_client,
    transmission_client,
):
    clients = {
        "deluge": deluge_client,
        "qbittorrent": qbittorrent_client,
        "rtorrent": rtorrent_client,
        "transmission": transmission_client,
    }

    source_client = clients[source_client_name]
    target_client = clients[target_client_name]

    torrent = testfiles / "Some-Release.torrent"
    torrent_data = bdecode(torrent.read_bytes())
    infohash = hashlib.sha1(bencode(torrent_data[b"info"])).hexdigest()
    source_client.add(torrent_data, testfiles, fast_resume=False)
    time.sleep(2)  # Weird bug with Deluge

    verify_torrent_state(
        source_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    source_client.stop(infohash)

    verify_torrent_state(
        source_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.STOPPED,
                "progress": 100.0,
            }
        ],
    )

    move_torrent(infohash, source_client, target_client)
    verify_torrent_state(
        target_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.STOPPED,
            }
        ],
    )

    target_client.start(infohash)

    verify_torrent_state(
        target_client,
        [
            {
                "infohash": infohash,
                "name": "Some-Release",
                "state": TorrentState.ACTIVE,
                "progress": 100.0,
            }
        ],
    )

    verify_torrent_state(
        source_client,
        [],
    )
    target_client.remove(infohash)
    verify_torrent_state(
        target_client,
        [],
    )
