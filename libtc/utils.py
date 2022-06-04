import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import publicsuffixlist


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
            file_path = Path(os.sep.join(os.fsdecode(p) for p in f[b"path"]))
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


def get_tracker_domain(tracker):
    url = urlparse(tracker)
    return get_tracker_domain.psl.privatesuffix(url.hostname)


# Takes significant time to instantiate (~100ms), so only do it once
get_tracker_domain.psl = publicsuffixlist.PublicSuffixList()


def move_files(source_path, target_path, files, preserve_parent_folder=False):
    """Move a file mapping from source_path to target_path and preserve permission et.al."""
    source_path = Path(source_path)
    target_path = Path(target_path)

    if not target_path.exists():
        target_path.mkdir()
        shutil.copystat(source_path, target_path)

    potential_removal_folders = set()
    if not preserve_parent_folder:
        potential_removal_folders.add(source_path)

    for f in files:
        source_file = source_path / f.path
        target_file = target_path / f.path

        while not target_file.parent.exists():
            source_file_parent = source_file.parent
            target_file_parent = target_file.parent

            while not (
                target_file_parent.parent.exists() and not target_file_parent.exists()
            ):
                source_file_parent = source_file_parent.parent
                target_file_parent = target_file_parent.parent

            if target_path not in target_file_parent.resolve().parents:
                raise Exception()
            target_file_parent.mkdir()
            shutil.copystat(source_file_parent, target_file_parent)

        source_parent_folder = source_file.parent
        while (
            source_path in source_parent_folder.parents
            and source_parent_folder not in potential_removal_folders
        ):
            potential_removal_folders.add(source_parent_folder)
            source_parent_folder = source_parent_folder.parent

        if target_path not in target_file.resolve().parents:
            raise Exception()

        source_file.rename(target_file)

    potential_removal_folders = sorted(potential_removal_folders, reverse=True)
    for folder in potential_removal_folders:
        if not list(folder.iterdir()):
            folder.rmdir()


class TorrentProblems:
    INVALID_PATH_SEGMENT = [b"", b".", b"..", b"/", b"\\"]
    BAD_CHARACTER_SET = [
        b"\x00",
        b"<",
        b">",
        b":",
        b"\\",
        b'"',
        b"/",
        b"\\",
        b"|",
        b"?",
        b"*",
    ]
    WINDOWS_RESERVED_NAMES = [
        b"con",
        b"prn",
        b"aux",
        b"nul",
        b"com1",
        b"com2",
        b"com3",
        b"com4",
        b"com5",
        b"com6",
        b"com7",
        b"com8",
        b"com9",
        b"lpt1",
        b"lpt2",
        b"lpt3",
        b"lpt4",
        b"lpt5",
        b"lpt6",
        b"lpt7",
        b"lpt8",
        b"lpt9",
    ]
    STRIPPED_PREFIX_POSTFIX = [b" ", b"."]
    MAX_PATH_LENGTH = 260
    EMOJIS = []  # TODO: add emojis that e.g. transmission chokes on


def rewrite_path(path, path_mapping):
    for k, v in path_mapping.items():
        try:
            p = path.relative_to(k)
            return v / p
        except ValueError:
            pass
    return path
