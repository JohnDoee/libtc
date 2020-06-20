from datetime import datetime

import pytz


class TorrentData:
    __slots__ = (
        "infohash",
        "name",
        "size",
        "state",
        "progress",
        "uploaded",
        "added",
        "tracker",
        "upload_rate",
        "download_rate",
        "label",
    )

    def __init__(
        self,
        infohash,
        name,
        size,
        state,
        progress,
        uploaded,
        added,
        tracker,
        upload_rate,
        download_rate,
        label,
    ):
        self.infohash = infohash
        self.name = name
        self.size = size
        self.state = state
        self.progress = progress
        self.uploaded = uploaded
        self.added = added
        self.tracker = tracker
        self.upload_rate = upload_rate
        self.download_rate = download_rate
        self.label = label

    def __repr__(self):
        return f"TorrentData(infohash={self.infohash!r}, name={self.name!r})"

    def serialize(self):
        data = {k: getattr(self, k) for k in self.__slots__}
        data["added"] = data["added"].isoformat().split(".")[0].split("+")[0]
        return data

    @classmethod
    def unserialize(cls, data):
        data = dict(data)
        data["added"] = datetime.strptime(data["added"], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=pytz.UTC
        )
        return cls(**data)


class TorrentState:
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class TorrentFile:
    __slots__ = (
        "path",
        "size",
        "progress",
    )

    def __init__(self, path, size, progress):
        self.path = path
        self.size = size
        self.progress = progress

    def __repr__(self):
        return f"TorrentFile(path={self.path!r}, size={self.size!r}), progress={self.progress!r})"

    def serialize(self):
        return {k: getattr(self, k) for k in self.__slots__}

    @classmethod
    def unserialize(cls, data):
        return cls(**data)
