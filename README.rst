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

License
---------------------------------

MIT