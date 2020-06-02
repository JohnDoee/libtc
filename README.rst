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