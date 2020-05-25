import os
from pathlib import Path


def is_legal_path(path):
    for p in path:
        if p in [".", ".."] or "/" in p:
            return False
    return True


def map_existing_files(torrent, path, add_name_to_folder=True):
    name = torrent[b"info"][b"name"].decode()

    files = []
    if b"files" in torrent[b"info"]:
        for f in torrent[b"info"][b"files"]:
            file_path = Path(os.sep.join(p.decode() for p in f[b"path"]))
            if add_name_to_folder:
                files.append((path / name / file_path, file_path, f[b"length"]))
            else:
                files.append((path / file_path, file_path, f[b"length"]))
    else:
        files.append((path / name, name, torrent[b"info"][b"length"]))

    result = []

    for fp, f, size in files:
        result.append((fp, f, size, fp.is_file() and fp.stat().st_size == size))

    return result


def find_existing_files(torrent, path, add_name_to_folder=True):
    """
    Checks if the files in a torrent exist,
    returns a tuple of found files, missing files, size found, size missing.
    """

    found, missing, found_size, missing_size = 0, 0, 0, 0

    for fp, f, size, found in map_existing_files(
        torrent, path, add_name_to_folder=add_name_to_folder
    ):
        if found:
            found += 1
            found_size += size
        else:
            missing += 1
            missing_size += size

    return found, missing, found_size, missing_size


def calculate_minimum_expected_data(torrent, path, add_name_to_folder=True):
    found, missing, found_size, missing_size = find_existing_files(
        torrent, path, add_name_to_folder=add_name_to_folder
    )
    if not found_size:
        return "none"
    elif found_size and missing_size:
        return "partial"
    else:
        return "full"


def has_minimum_expected_data(expected_data, actual_data):
    if expected_data == "none":
        return True
    elif expected_data == "partial" and actual_data in ["partial", "full"]:
        return True
    elif expected_data == actual_data == "full":
        return True
    return False
