#!/usr/bin/env python

"""
yaml class that can load yaml files with includes and envvars and check for duplicate keys.
"""

import functools
import json
import os
from typing import Any, Union

import yaml
from yaml.constructor import ConstructorError

LegacyYAMLLoader = (os.getenv("LEGACY_YAML_LOADER", "false")).lower() == "true"


def no_duplicates_constructor(
    loader: yaml.Loader, node: yaml.Node, deep: bool = False
) -> Union[Any, Exception]:
    """Check for duplicate keys."""
    try:
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            value = loader.construct_object(value_node, deep=deep)
            if (key in mapping) and (not LegacyYAMLLoader):
                return ConstructorError(
                    "While constructing a mapping",
                    node.start_mark,
                    f"found duplicate key ({key})",
                    key_node.start_mark,
                )
            mapping[key] = value

        return loader.construct_mapping(node, deep)
    except Exception as e:
        return e


yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates_constructor
)


class ExtLoaderMeta(type):
    """External yaml loader metadata class."""

    def __new__(
        metacls, __name__: str, __bases__: Any, __dict__: Any
    ) -> Union[Any, Exception]:
        """Add constructers to class."""
        try:
            cls = super().__new__(metacls, __name__, __bases__, __dict__)

            # register the include constructors on the class
            cls.add_constructor("!include", cls.construct_include)
            cls.add_constructor("!envvar", cls.construct_envvar)
            return cls
        except Exception as e:
            return e


class ExtLoader(yaml.Loader, metaclass=ExtLoaderMeta):
    """YAML Loader with additional constructors."""

    def __init__(self, stream: Any) -> None:
        """Initialise Loader."""
        try:
            streamdata = stream if isinstance(stream, str) else stream.name
            self._root = os.path.split(streamdata)[0]
        except AttributeError:
            self._root = os.path.curdir
        super().__init__(stream)

    def construct_include(self, node: yaml.Node) -> Union[Any, Exception]:
        """Include file referenced at node."""
        try:
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
                    includedata = []
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
        except Exception as e:
            return e

    def construct_envvar(self, node: yaml.Node) -> Union[str, None, Exception]:
        """Expand env variable at node"""
        try:
            return os.getenv((node.value).strip(), "")
        except Exception as e:
            return e


def load(*args: Any, **kwargs: Any) -> Union[Any, Exception]:
    try:
        return functools.partial(yaml.load, Loader=ExtLoader)(*args, **kwargs)
    except Exception as e:
        return e
