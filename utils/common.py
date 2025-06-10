"""
common functions
"""

import os
import re
from collections.abc import MutableMapping

import utils.yaml_class as yaml

__all__ = ["env_override", "regex_replace", "flatten_dict", "to_yaml", "merge_dicts"]


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(d: MutableMapping, parent_key: str = "", sep: str = "."):
    return dict(_flatten_dict_gen(d, parent_key, sep))


def regex_replace(s, find, replace):
    """A non-optimal implementation of a regex filter for use in our Jinja2 template processing"""
    return re.sub(find, replace, s)


def env_override(value, key):
    """Can be used to pull env vars into templates"""
    return os.getenv(key, value)


def to_yaml(value):
    """convert dicts to yaml"""
    if isinstance(value, dict):
        return yaml.dump(value)
    elif isinstance(value, str):
        return value


def pretty(d, indent=10, result=""):
    """Pretty up output in Jinja template"""
    for key, value in d.iteritems():
        result += " " * indent + str(key)
        if isinstance(value, dict):
            result = pretty(value, indent + 2, result + "\n")
        else:
            result += ": " + str(value) + "\n"
    return result


def merge_dicts(a, b, path=None):
    """ "merges b into a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]

        else:
            a[key] = b[key]
    return a


def parse_checksum_file(file_path: str):
    checksums = {}
    with open(file_path, "r") as file:
        for line in file:
            checksum, filepath = line.strip().split("  ", 1)
            checksums[filepath] = checksum
    return checksums


def compare_checksums(checksums1: str, checksums2: str, include_same=False):
    differences = []
    for filepath, checksum1 in checksums1.items():
        base_filename = filepath.split("/")[-1]
        if filepath in checksums2:
            checksum2 = checksums2[filepath]
            if checksum1 != checksum2:
                differences.append(
                    {
                        "filepath": filepath,
                        "base_filename": base_filename,
                        "source_id": base_filename.split(".")[0],
                        "source": checksum1,
                        "changetype": "change",
                    }
                )
            elif include_same:
                differences.append(
                    {
                        "filepath": filepath,
                        "base_filename": base_filename,
                        "source_id": base_filename.split(".")[0],
                        "source": checksum1,
                        "changetype": "same",
                    }
                )
        else:
            differences.append(
                {
                    "filepath": filepath,
                    "base_filename": base_filename,
                    "source_id": base_filename.split(".")[0],
                    "source": checksum1,
                    "changetype": "delete_dest",
                }
            )

    for filepath, checksum2 in checksums2.items():
        base_filename = filepath.split("/")[-1]
        if filepath not in checksums1:
            differences.append(
                {
                    "filepath": filepath,
                    "base_filename": base_filename,
                    "source_id": base_filename.split(".")[0],
                    "source": checksum2,
                    "changetype": "delete_source",
                }
            )

    return differences
