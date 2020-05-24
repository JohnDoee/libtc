class LibTorrentClientException(Exception):
    """Base exception"""


class FailedToExecuteException(LibTorrentClientException):
    """Failed to execute command on torrent client"""
