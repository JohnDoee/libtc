================================
Lib Torrent Client
================================

This is a library to interface with a variety of torrent clients,
abstracting away the need to understand a specific client api.

.. image:: https://github.com/JohnDoee/libtc/actions/workflows/main.yml/badge.svg?branch=master

Requirements
--------------------------------

* Python 3.6 or higher


Installation
--------------------------------

.. code-block:: bash

    pip install libtc


Features
--------------------------------

Clients:

* rtorrent
* Deluge
* Transmission
* qBittorrent
* LilTorrent (local-to-remote interface for other clients)

Methods:

* List torrents
* Stop/start torrents
* Add/remove torrents
* Retrieve the actual .torrent file

Other:

* Verify local content exist
* Discover client config to autoconfigure clients
* Move torrents between clients

Commandline interface
---------------------------------

The commandline interface allows for basic operations on torrents:

.. code-block:: bash

    # See available commands
    libtc --help

    # See help for individual command
    libtc "transmission+http://127.0.0.1:9091/transmission/rpc?session_path=%7E/.config/transmission" list --help

    # Execute a command
    libtc "transmission+http://127.0.0.1:9091/transmission/rpc?session_path=%7E/.config/transmission" list

    # Move torrent with infohash da39a3ee5e6b4b0d3255bfef95601890afd80709 from transmission to deluge
    libtc "transmission+http://127.0.0.1:9091/transmission/rpc?session_path=%7E/.config/transmission" move \
          "da39a3ee5e6b4b0d3255bfef95601890afd80709" \
          "deluge://localclient:da39a3ee5e6b4b0d3255bfef95601890afd80709@127.0.0.1:58846?session_path=%7E/.config/deluge"

Session path & fetching torrents
---------------------------------

This library can find and use the actual torrent files but this is generally not possible to the APIs.
Therefore it must know where the torrents are stored locally.

These folders must contain the actual `.torrent` files.

A list of relative torrent paths can be found here:

Deluge
  <session_path>/state/

qBittorrent
  <session_path>/data/BT_backup/

rtorrent
  <session_path>/

Transmission
  <session_path>/torrents/

An example could be transmission configured with `session_path=/tmp/transmission/` then the actual torrent files would
be store in `/tmp/transmission/torrents/`.

These are subject to change depending on how it really works out with different client versions.

URL Syntax
---------------------------------

The query part of urls are generally optional

Deluge
==============================

Syntax: :code:`deluge://<username>:<password>@<hostname_or_ip>:<port>?session_path=<path_to_session>`

Example: :code:`deluge://localclient:da39a3ee5e6b4b0d3255bfef95601890afd80709@127.0.0.1:58846?session_path=%7E/.config/deluge`

LilTorrent
==============================

Multiple path mappings can be added, they are joined by a `;` - apikey is mandatory.

Syntax: :code:`liltorrent+<protocol>://<hostname_or_ip>:<port>?apikey=<apikey>&path_mapping=<rewritten_from_path>:<rewritten_to_path>;<another_rewritten_from_path>:<another_rewritten_to_path>`

Example: :code:`liltorrent+http://localhost:10977?apikey=secret&path_mapping=/a/%3A/b/%3B/s/t/%3A/f/`

This example changes :code:`/a/horse.gif` to :code:`/b/horse.gif`

qBittorrent
==============================

Syntax: :code:`qbittorrent+<protocol>://<username>:<password>@<hostname_or_ip>:<port>?session_path=<path_to_session>`

Example: :code:`qbittorrent+http://admin:adminadmin@localhost:8080?session_path=%7E/.config/qBittorrent`

rtorrent
==============================

Syntax: :code:`rtorrent+<protocol>://<path_or_hostname>:<optional_port>?session_path=<path_to_session>&torrent_temp_path=<path_to_accessible_tmp>`

Example: :code:`rtorrent+scgi:///path/to/scgi.socket?session_path=%7E/.rtorrent/&torrent_temp_path=%7E/.rtorrent/tmp-libtc`

Example: :code:`rtorrent+scgi://127.0.0.1:5000?session_path=%7E/.rtorrent/&torrent_temp_path=%7E/.rtorrent/tmp-libtc`

Example: :code:`rtorrent+http://127.0.0.1:8000/SCGI?session_path=%7E/.rtorrent/&torrent_temp_path=%7E/.rtorrent/tmp-libtc`

Transmission
==============================

Syntax: :code:`transmission+<protocol>://<hostname>:<port>?session_path=<path_to_session>`

Example: :code:`transmission+http://127.0.0.1:9091/transmission/rpc?session_path=%7E/.config/transmission`

LilTorrent usage
---------------------------------

This layer can work as an abstraction layer between local clients in different environments,
e.g. in a docker container.

.. code-block:: bash

    pip install libtc[liltorrent]

    LILTORRENT_APIKEY=secretapikey LILTORRENT_CLIENT=rtorrent:///path/to/scgi.socket liltorrent

* `LILTORRENT_APIKEY` is the apikey that the server is accessible through
* `LILTORRENT_CLIENT` is a client URL

Config file syntax
---------------------------------

These examples use .toml format, while the actual parsing logic is agnostic to on-disk format, it's the recommended one.

The display_name is the name shown when client is used. If it is not set, then the config file key is used,
e.g. `[clients.another-transmission]` is called `another-transmission` if no display_name is set.

The URL config as described above can also be used and is seen in the last example as `deluge-url`.

Each key must be unique, e.g. you cannot have two clients with the same key, e.g. two `[clients.the-transmission]`

.. code-block:: toml

    [clients]

    [clients.deluge]
    display_name = "A Deluge"
    client_type = "deluge"
    host = "127.0.0.1"
    port = 58846
    username = "localclient"
    password = "secretpassword"
    session_path = "~/.config/deluge/"

    [clients.the-transmission]
    display_name = "Some transmission"
    client_type = "transmission"
    url = "http://127.0.0.1:9091/transmission/rpc"
    session_path = "~/.config/transmission-daemon/"

    [clients.another-transmission]
    display_name = "Horse transmission"
    client_type = "transmission"
    url = "http://127.0.0.1:9092/transmission/rpc"
    session_path = "~/.config/transmission-daemon2/"

    [clients.rtorrent]
    display_name = "rtorrent"
    client_type = "rtorrent"
    url = "scgi://127.0.0.1:5000"
    session_path = "~/.rtorrent/"

    [clients.another-qbittorrent]
    display_name = "qBittorrent 1"
    client_type = "qbittorrent"
    url = "http://localhost:8080/"
    username = "admin"
    password = "adminadmin"
    session_path = "~/.config/qbittorrent/"

    # This is an example of using the url syntax
    [clients.deluge-url]
    display_name = "Deluge url"
    client_url = "deluge://localclient:da39a3ee5e6b4b0d3255bfef95601890afd80709@127.0.0.1:58846?session_path=%7E/.config/deluge"

    [clients.rtorrent-with-label]
    display_name = "rtorrent"
    client_type = "rtorrent"
    url = "scgi://127.0.0.1:5000"
    session_path = "~/.rtorrent/"
    label = "alabel"

    [clients.deluge-with-label]
    display_name = "A Deluge"
    client_type = "deluge"
    host = "127.0.0.1"
    port = 58846
    username = "localclient"
    password = "secretpassword"
    session_path = "~/.config/deluge/"
    label = "alabel"

License
---------------------------------

MIT