================================
Lib Torrent Client
================================

This is a library to interface with a variety of torrent clients,
abstracting away the need to understand a specific client api.

.. image:: https://travis-ci.org/JohnDoee/libtc.svg?branch=master
    :target: https://travis-ci.org/JohnDoee/libtc

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


Move torrent between clients:
==============================


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

License
---------------------------------

MIT