"""
common functions
"""

import os
import re
import subprocess
#from collections.abc import MutableMapping
from typing import Any, Dict, Generator, List, MutableMapping, Union

import metagit.core.utils.yaml_class as yaml

__all__ = ["env_override", "regex_replace", "flatten_dict", "to_yaml", "merge_dicts", "open_editor", "create_vscode_workspace"]


def create_vscode_workspace(project_name: str, repo_paths: List[str]) -> Union[str, Exception]:
    """
    Create VS Code workspace file content.
    
    Args:
        project_name: The name of the project
        repo_paths: List of repository paths to include in the workspace
        
    Returns:
        JSON string representing the VS Code workspace file content
    """
    try:
        workspace_data = {
            "folders": [],
            "settings": {
                "files.exclude": {
                    "**/.git": True,
                    "**/.DS_Store": True,
                    "**/node_modules": True,
                    "**/__pycache__": True,
                    "**/*.pyc": True
                },
                "search.exclude": {
                    "**/node_modules": True,
                    "**/bower_components": True,
                    "**/*.code-search": True
                }
            },
            "extensions": {
                "recommendations": [
                    "ms-python.python",
                    "ms-vscode.vscode-json",
                    "redhat.vscode-yaml",
                    "ms-vscode.vscode-typescript-next"
                ]
            }
        }
        
        # Add each repository as a folder in the workspace
        for repo_path in repo_paths:
            workspace_data["folders"].append({
                "name": os.path.basename(repo_path),
                "path": f"./{os.path.basename(repo_path)}"
            })
        
        # Convert to JSON string
        import json
        return json.dumps(workspace_data, indent=2)
    except Exception as e:
        return e


def open_editor(editor: str, path: str) -> Union[None, Exception]:
    """
    Open a path in the specified editor in an OS-agnostic way.
    
    Args:
        editor: The editor command to use (e.g., 'code', 'vim', 'nano')
        path: The path to open in the editor
        
    Returns:
        None on success, Exception on failure
    """
    try:
        # Ensure the path exists
        if not os.path.exists(path):
            return Exception(f"Path does not exist: {path}")
        
        # Use subprocess to open the editor
        # This works cross-platform as subprocess handles the differences
        result = subprocess.run([editor, path], capture_output=True, text=True)
        
        if result.returncode != 0:
            return Exception(f"Failed to open editor '{editor}': {result.stderr}")
        
        return None
    except FileNotFoundError:
        return Exception(f"Editor '{editor}' not found in PATH")
    except Exception as e:
        return e


def _flatten_dict_gen(
    d: MutableMapping, parent_key: str, sep: str
) -> Generator[Any, None, None]:
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(
    d: MutableMapping, parent_key: str = "", sep: str = "."
) -> Union[Dict[Any, Any], Exception]:
    try:
        return dict(_flatten_dict_gen(d, parent_key, sep))
    except Exception as e:
        return e


def regex_replace(s: str, find: str, replace: str) -> Union[str, Exception]:
    """A non-optimal implementation of a regex filter for use in our Jinja2 template processing"""
    try:
        return re.sub(find, replace, s)
    except Exception as e:
        return e


def env_override(value: str, key: str) -> Union[str, None, Exception]:
    """Can be used to pull env vars into templates"""
    try:
        return os.getenv(key, value)
    except Exception as e:
        return e


def to_yaml(value: Any) -> Union[str, Any, Exception]:
    """convert dicts to yaml"""
    try:
        if isinstance(value, dict):
            return yaml.dump(value)
        elif isinstance(value, str):
            return value
        return value
    except Exception as e:
        return e


def pretty(
    d: Dict[Any, Any], indent: int = 10, result: str = ""
) -> Union[str, Exception]:
    """Pretty up output in Jinja template"""
    try:
        for key, value in d.items():
            result += " " * indent + str(key)
            if isinstance(value, dict):
                pretty_result = pretty(value, indent + 2, result + "\n")
                if isinstance(pretty_result, Exception):
                    return pretty_result
                result = pretty_result
            else:
                result += ": " + str(value) + "\n"
        return result
    except Exception as e:
        return e


def merge_dicts(a: Dict, b: Dict, path: List = None) -> Union[Dict, Exception]:
    """ "merges b into a"""
    try:
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    merge_result = merge_dicts(a[key], b[key], path + [str(key)])
                    if isinstance(merge_result, Exception):
                        return merge_result
                elif a[key] == b[key]:
                    pass  # same leaf value
                else:
                    a[key] = b[key]

            else:
                a[key] = b[key]
        return a
    except Exception as e:
        return e


def parse_checksum_file(file_path: str) -> Union[Dict[str, str], Exception]:
    try:
        checksums = {}
        with open(file_path) as file:
            for line in file:
                checksum, filepath = line.strip().split("  ", 1)
                checksums[filepath] = checksum
        return checksums
    except Exception as e:
        return e


def compare_checksums(
    checksums1: Dict[str, str], checksums2: Dict[str, str], include_same: bool = False
) -> Union[List[Dict[str, str]], Exception]:
    try:
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
    except Exception as e:
        return e
