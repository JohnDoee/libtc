import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from libtc import RTorrentClient

from .basetest import *

RTORRENT_CONFIG = r"""#############################################################################
# A minimal rTorrent configuration that provides the basic features
# you want to have in addition to the built-in defaults.
#
# See https://github.com/rakshasa/rtorrent/wiki/CONFIG-Template
# for an up-to-date version.
#############################################################################


## Instance layout (base paths)
method.insert = cfg.basedir,  private|const|string, (cat,"%%TMPDIR%%/")
method.insert = cfg.download, private|const|string, (cat,(cfg.basedir),"download/")
method.insert = cfg.logs,     private|const|string, (cat,(cfg.basedir),"log/")
method.insert = cfg.logfile,  private|const|string, (cat,(cfg.logs),"rtorrent-",(system.time),".log")
method.insert = cfg.session,  private|const|string, (cat,(cfg.basedir),".session/")
method.insert = cfg.watch,    private|const|string, (cat,(cfg.basedir),"watch/")

## Create instance directories
execute.throw = sh, -c, (cat,\
    "mkdir -p \"",(cfg.download),"\" ",\
    "\"",(cfg.logs),"\" ",\
    "\"",(cfg.session),"\" ",\
    "\"",(cfg.watch),"/load\" ",\
    "\"",(cfg.watch),"/start\" ")

## Listening port for incoming peer traffic (fixed; you can also randomize it)
network.port_range.set = 50000-50000
network.port_random.set = no


## Tracker-less torrent and UDP tracker support
## (conservative settings for 'private' trackers, change for 'public')
dht.mode.set = disable
protocol.pex.set = no

trackers.use_udp.set = no


## Peer settings
throttle.max_uploads.set = 100
throttle.max_uploads.global.set = 250

throttle.min_peers.normal.set = 20
throttle.max_peers.normal.set = 60
throttle.min_peers.seed.set = 30
throttle.max_peers.seed.set = 80
trackers.numwant.set = 80

protocol.encryption.set = allow_incoming,try_outgoing,enable_retry


## Limits for file handle resources, this is optimized for
## an `ulimit` of 1024 (a common default). You MUST leave
## a ceiling of handles reserved for rTorrent's internal needs!
network.http.max_open.set = 50
network.max_open_files.set = 600
network.max_open_sockets.set = 300


## Memory resource usage (increase if you have a large number of items loaded,
## and/or the available resources to spend)
pieces.memory.max.set = 1800M
network.xmlrpc.size_limit.set = 4M


## Basic operational settings (no need to change these)
session.path.set = (cat, (cfg.session))
directory.default.set = (cat, (cfg.download))
log.execute = (cat, (cfg.logs), "execute.log")
#log.xmlrpc = (cat, (cfg.logs), "xmlrpc.log")
execute.nothrow = sh, -c, (cat, "echo >",\
    (session.path), "rtorrent.pid", " ",(system.pid))


## Other operational settings (check & adapt)
encoding.add = utf8
system.umask.set = 0027
system.cwd.set = (directory.default)
network.http.dns_cache_timeout.set = 25

method.insert = system.startup_time, value|const, (system.time)
method.insert = d.data_path, simple,\
    "if=(d.is_multi_file),\
        (cat, (d.directory), /),\
        (cat, (d.directory), /, (d.name))"
method.insert = d.session_file, simple, "cat=(session.path), (d.hash), .torrent"

## Run the rTorrent process as a daemon in the background
## (and control via XMLRPC sockets)
system.daemon.set = true
network.scgi.open_local = (cat,(session.path),rpc.socket)
execute.nothrow = chmod,770,(cat,(session.path),rpc.socket)


## Logging:
##   Levels = critical error warn notice info debug
##   Groups = connection_* dht_* peer_* rpc_* storage_* thread_* tracker_* torrent_*
print = (cat, "Logging to ", (cfg.logfile))
log.open_file = "log", (cfg.logfile)
log.add_output = "info", "log"
#log.add_output = "tracker_debug", "log"

### END of rtorrent.rc ###"""


@pytest.fixture(scope="module")
def client():
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        config_content = RTORRENT_CONFIG.replace("%%TMPDIR%%", str(tmp_path))
        config_file = tmp_path / ".rtorrent.rc"
        with open(config_file, "w") as f:
            f.write(config_content)

        p = subprocess.Popen(["rtorrent", "-n", "-o", f"import={config_file!s}"])
        client = RTorrentClient(
            f"scgi://{tmp_path!s}/.session/rpc.socket", tmp_path / ".session"
        )
        for _ in range(30):
            if client.test_connection():
                break
            time.sleep(0.1)
        else:
            p.kill()
            pytest.fail("Unable to start rtorrent")
        yield client
        p.kill()


def test_serialize_configuration(client):
    url = client.serialize_configuration()
    url, query = url.split("?")
    assert re.match(r"rtorrent\+scgi:///.+/.session/rpc.socket", url)
    assert query.startswith("session_path=")
