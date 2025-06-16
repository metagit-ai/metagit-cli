#!/usr/bin/env python

"""
yaml class that can load yaml files with includes and envvars and check for duplicate keys.
"""


import functools
import json
import os

import yaml
from yaml.constructor import ConstructorError

LegacyYAMLLoader = (os.getenv("LEGACY_YAML_LOADER", "false")).lower() == "true"


def no_duplicates_constructor(loader, node, deep=False):
    """Check for duplicate keys."""

    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if (key in mapping) and (not LegacyYAMLLoader):
            raise ConstructorError(
                "While constructing a mapping",
                node.start_mark,
                "found duplicate key (%s)" % key,
                key_node.start_mark,
            )
        mapping[key] = value

    return loader.construct_mapping(node, deep)


yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates_constructor
)


class ExtLoaderMeta(type):
    """External yaml loader metadata class."""

    def __new__(metacls, __name__, __bases__, __dict__):
        """Add constructers to class."""
        cls = super().__new__(metacls, __name__, __bases__, __dict__)

        # register the include constructors on the class
        cls.add_constructor("!include", cls.construct_include)
        cls.add_constructor("!envvar", cls.construct_envvar)
        return cls


class ExtLoader(yaml.Loader, metaclass=ExtLoaderMeta):
    """YAML Loader with additional constructors."""

    def __init__(self, stream):
        """Initialise Loader."""
        try:
            if isinstance(stream, str):
                streamdata = stream
            else:
                streamdata = stream.name
            self._root = os.path.split(streamdata)[0]
        except AttributeError:
            self._root = os.path.curdir
        super().__init__(stream)

    def construct_include(self, node):
        """Include file referenced at node."""
        file_name = os.path.abspath(
            os.path.join(self._root, self.construct_scalar(node))
        )
        extension = os.path.splitext(file_name)[1].lstrip(".")
        with open(file_name) as f:
            if extension in ("yaml", "yml"):
                data = yaml.load(f, Loader=yaml.FullLoader)
            elif extension in ("json",):
                data = json.load(f)
            else:
                includedata = list()
                line = f.readline()
                cnt = 0
                while line:
                    includedata.append(line.strip())
                    line = f.readline()
                    cnt += 1
                if cnt == 1:
                    data = "".join(includedata)
                else:
                    data = '"' + "\\n".join(includedata) + '"'
        return data

    def construct_envvar(self, node):
        """Expand env variable at node"""
        return os.getenv((node.value).strip(), "")


load = functools.partial(yaml.load, Loader=ExtLoader)
