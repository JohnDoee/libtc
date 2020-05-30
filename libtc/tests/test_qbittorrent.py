import json
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from libtc import QBittorrentClient

from .basetest import *

QBITTORRENT_CONFIG = r"""[LegalNotice]
Accepted=true

[Network]
Cookies=@Invalid()
"""


@pytest.fixture(scope="module", params=[True, False,])
def client(request):
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        tmp_config_path = tmp_path / "qBittorrent" / "config" / "qBittorrent_new.conf"
        tmp_config_path.parent.mkdir(parents=True)
        with open(tmp_config_path, "w") as f:
            f.write(QBITTORRENT_CONFIG)

        p = subprocess.Popen(["qbittorrent-nox", f"--profile={tmp_path!s}"])
        client = QBittorrentClient(
            "http://localhost:8080/",
            "admin",
            "adminadmin",
            str(tmp_path / "qBittorrent"),
        )
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start qbittorrent")
        client.call(
            "post",
            "/api/v2/app/setPreferences",
            data={"json": json.dumps({"create_subfolder_enabled": request.param})},
        )
        yield client
        if (
            client.call("get", "/api/v2/app/preferences").json()[
                "create_subfolder_enabled"
            ]
            != request.param
        ):
            pytest.fail("Settings were modified when they should not have been")
        p.kill()


def test_serialize_configuration(client):
    url = client.serialize_configuration()
    url, query = url.split("?")
    assert url == "qbittorrent+http://admin:adminadmin@localhost:8080/"
    assert query.startswith("session_path=")
