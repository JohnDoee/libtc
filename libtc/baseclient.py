from abc import ABCMeta, abstractmethod, abstractproperty


class BaseClient(metaclass=ABCMeta):
    @abstractproperty
    def identifier():
        """
        Text string used to identify this client
        """

    @abstractmethod
    def list():
        """
        Return a list of `TorrentData`
        """

    @abstractmethod
    def list_active():
        """
        Return a list of `TorrentData` with active torrents
        """

    @abstractmethod
    def start(infohash):
        """
        Start a torrent with a given infohash
        """

    @abstractmethod
    def stop(infohash):
        """
        Stop a torrent with a given infohash
        """

    @abstractmethod
    def test_connection():
        """
        Test if the client is reachable.
        """

    @abstractmethod
    def add(
        torrent,
        destination_path,
        fast_resume=False,
        add_name_to_folder=True,
        minimum_expected_data="none",
    ):
        """
        Add a new torrent,

        torrent: decoded torrentfile
        destination_path: path where to store the data
        fast_resume: Try to fast-resume
        add_name_to_folder: add name from torrent to the folder, only multifile torrent
        minimum_expected_data: check local data and make sure minimum is there.
          Choices are: none, partial, full
        """

    @abstractmethod
    def remove(infohash):
        """
        Remove a torrent with a given infohash
        """

    @abstractmethod
    def retrieve_torrentfile(infohash):
        """
        Retrieve the torrent file and returns it content
        """
