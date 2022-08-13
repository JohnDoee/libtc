================================
Changelog
================================

Version 1.3.4 (13-08-2022)
--------------------------------

* Added: Label support for qbittorrent

Version 1.3.3 (18-06-2022)
--------------------------------

* Change: rtorrent shares more information about failures to add torrents

Version 1.3.2 (15-06-2022)
--------------------------------

* Bugfix: symlinks should not be resolved

Version 1.3.1 (03-06-2022)
--------------------------------

* Bugfix: Pypi broke

Version 1.3.0 (03-06-2022)
--------------------------------

* Added: Test matrix for multiple ubuntu releases

* Change: Bumped and unbounded version of some requirements

* Bugfix: Changed how qbittorrent handles subfolders
* Bugfix: Transmission 3 torrent location
* Bugfix: Fixed qbittorrent torrent file retrival problem in newer versions

Version 1.2.3 (30-05-2022)
--------------------------------

* Added: Label support to rtorrent and deluge

Version 1.2.2 (22-05-2022)
--------------------------------

* Added: Parse function from config to map of clients

* Bugfix: Added missing implementations for the test client

Version 1.2.1 (08-04-2022)
--------------------------------

* Change: Bumped click version

* Bugfix: Added missing implementations for the fake client

Version 1.2.0 (08-04-2022)
--------------------------------

* Added: move_torrent support

* Change: Session usage with transmission to reuse conneciton

Version 1.1.1 (03-11-2021)
--------------------------------

* Change: Transmission supports basic auth

* Bugfix: Ensuring Automatic Torrent Management Mode is disabled when using qBittorrent
* Bugfix: Deluge 1 bug with download_location
* Bugfix: Transmission bug with progress percentage on files in reverse

Version 1.1.0 (22-06-2020)
--------------------------------

* Added: get_files to list files in a given torrent

* Bugfix: Problem with start/stop of deluge 1 torrents

Version 1.0.0 (10-05-2020)
--------------------------------

* Initial release