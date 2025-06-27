#! /usr/bin/env python3
"""
File reader tool for the detect flow
"""

import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel

from metagit import DATA_PATH


def is_binary_file(file_path: str) -> bool:
    """
    Check if a file is binary by examining its content.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is binary, False if it's text
    """
    try:
        with open(file_path, "rb") as f:
            # Read first 1024 bytes to check for binary content
            chunk = f.read(1024)
            if not chunk:
                return False

            # Check for null bytes (common in binary files)
            if b"\x00" in chunk:
                return True

            # Check if the chunk contains mostly printable ASCII characters
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7F)))
            return bool(chunk.translate(None, text_chars))

    except (IOError, OSError):
        # If we can't read the file, assume it's not binary
        return False


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError):
        return 0


def list_files(directory_path: str) -> List[str]:
    """
    List all files in a directory recursively.

    Args:
        directory_path: Path to the directory

    Returns:
        List of file paths
    """
    try:
        files = []
        for root, _, filenames in os.walk(directory_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files
    except (OSError, IOError):
        return []


def read_file_lines(file_path: str) -> List[str]:
    """
    Read all lines from a file.

    Args:
        file_path: Path to the file

    Returns:
        List of lines (without newline characters)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f]
    except (OSError, IOError):
        return []


def write_file_lines(file_path: str, lines: List[str]) -> bool:
    """
    Write lines to a file.

    Args:
        file_path: Path to the file
        lines: List of lines to write

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        return True
    except (OSError, IOError):
        return False


def copy_file(source_path: str, dest_path: str) -> bool:
    """
    Copy a file from source to destination.

    Args:
        source_path: Path to source file
        dest_path: Path to destination file

    Returns:
        True if successful, False otherwise
    """
    try:
        import shutil

        shutil.copy2(source_path, dest_path)
        return True
    except (OSError, IOError):
        return False


def remove_file(file_path: str) -> bool:
    """
    Remove a file.

    Args:
        file_path: Path to the file to remove

    Returns:
        True if successful, False otherwise
    """
    try:
        os.remove(file_path)
        return True
    except (OSError, IOError):
        return False


def make_dir(dir_path: str) -> bool:
    """
    Create a directory.

    Args:
        dir_path: Path to the directory to create

    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except (OSError, IOError):
        return False


def remove_dir(dir_path: str) -> bool:
    """
    Remove a directory and its contents.

    Args:
        dir_path: Path to the directory to remove

    Returns:
        True if successful, False otherwise
    """
    try:
        import shutil

        shutil.rmtree(dir_path)
        return True
    except (OSError, IOError):
        return False


class FileTypeInfo(BaseModel):
    kind: str
    type: str


class FileTypeWithPercent(BaseModel):
    kind: str
    percent: float


class DirectoryDetails(BaseModel):
    path: str
    num_files: int
    file_types: Dict[str, List[FileTypeWithPercent]]
    subpaths: List["DirectoryDetails"]


class FileExtensionLookup:
    def __init__(
        self, extension_data: str = os.path.join(DATA_PATH, "file-types.json")
    ):
        # Parse JSON data
        try:
            with open(extension_data, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON data: {exc}") from exc

        # Create extension to info mapping for O(1) lookup
        self._lookup: Dict[str, FileTypeInfo] = {}

        # Handle the JSON structure which has data wrapped in "extensions" key
        if isinstance(data, dict) and "extensions" in data:
            items = data["extensions"]
        else:
            items = data

        for item in items:
            if isinstance(item, dict):
                kind = item.get("kind", "")
                file_type = item.get("type", "")
                extensions = item.get("extensions", [])

                # Store each extension with its corresponding info
                info = FileTypeInfo(kind=kind, type=file_type)
                for ext in extensions:
                    # Normalize extension (lowercase, ensure leading dot)
                    ext = ext.lower()
                    if not ext.startswith("."):
                        ext = f".{ext}"
                    self._lookup[ext] = info

    def get_file_info(self, filename: str) -> Optional[FileTypeInfo]:
        """
        Look up file type information based on file extension.

        Args:
            filename: File name or path to check

        Returns:
            FileTypeInfo tuple containing name and type, or None if not found
        """
        # Extract extension and normalize
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        return self._lookup.get(ext)


def parse_gitignore(ignore_file: Path) -> Set[str]:
    """
    Parse .gitignore files.

    Args:
        directory_path: Path to the current directory to check for .gitignore
        base_path: Base directory path for the analysis (root of the tree)

    Returns:
        Set of patterns to ignore (combined from all .gitignore files in the path)
    """
    ignore_patterns = set()

    if Path(ignore_file).exists():
        try:
            with open(ignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        ignore_patterns.add(line)
        except Exception:
            pass

    return ignore_patterns


def should_ignore_path(path: Path, ignore_patterns: Set[str], base_path: Path) -> bool:
    """
    Check if a path should be ignored based on ignored patterns.

    Args:
        path: Path to check
        ignore_patterns: Set of patterns from .gitignore files
        base_path: Base directory path for relative pattern matching

    Returns:
        True if the path should be ignored, False otherwise
    """
    if not ignore_patterns:
        return False

    # Get relative path from base directory
    try:
        relative_path = path.relative_to(base_path)
    except ValueError:
        # Path is not relative to base, use the path name
        relative_path = Path(path.name)

    relative_str = str(relative_path)

    # Check each pattern
    for pattern in ignore_patterns:
        # Handle file patterns
        if (
            fnmatch.fnmatch(relative_str, pattern)
            or fnmatch.fnmatch(path.name, pattern)
            or fnmatch.fnmatch(relative_str, pattern)
        ):
            return True

    return False


def directory_details(
    target_path: str,
    file_lookup: FileExtensionLookup,
    ignore_patterns: Optional[Set[str]] = None,
    resolve_path: bool = False,
) -> DirectoryDetails:
    """
    Recursively walks a directory and builds detailed metadata structure using FileExtensionLookup.

    Args:
        target_path: Path to the target directory to analyze
        file_lookup: Single instance of FileExtensionLookup for file type information
        ignore_patterns: Set of patterns to ignore (applied to all subdirectories)

    Returns:
        DirectoryDetails: NamedTuple containing directory structure and detailed file statistics grouped by category
    """
    path = Path(target_path)
    ignore_file = os.path.join(path, ".gitignore")
    ignore_patterns = ignore_patterns or set()
    ignore_patterns = ignore_patterns.union(parse_gitignore(ignore_file))

    if not path.is_dir():
        raise ValueError(f"Path {target_path} is not a directory")

    # Initialize data structures
    file_type_counts: Dict[str, Dict[str, int]] = {
        "programming": {},
        "data": {},
        "markup": {},
        "prose": {},
    }
    subpaths: List[DirectoryDetails] = []
    num_files = 0

    # Process directory contents
    for item in path.iterdir():
        # Always ignore .git folders
        if item.name == ".git":
            continue
        # Check if item should be ignored based on ignore_patterns
        if should_ignore_path(item, ignore_patterns, Path(target_path)):
            continue
        if item.is_dir():
            # Recursively process subdirectory with the same ignore_patterns
            sub_metadata = directory_details(
                str(item), file_lookup, ignore_patterns, resolve_path
            )
            subpaths.append(sub_metadata)
        else:
            # Count file and get detailed type information
            num_files += 1
            file_info = file_lookup.get_file_info(item.name)
            if file_info:
                # Group by type category and count by kind
                category = file_info.type
                kind = file_info.kind
                if category in file_type_counts:
                    file_type_counts[category][kind] = (
                        file_type_counts[category].get(kind, 0) + 1
                    )

    # Convert counts to percentages based on total files in directory
    file_types_by_category: Dict[str, List[FileTypeWithPercent]] = {}

    if num_files > 0:  # Only calculate percentages if there are files
        for category, kinds in file_type_counts.items():
            if kinds:  # Only include categories that have files
                file_types_by_category[category] = [
                    FileTypeWithPercent(
                        kind=kind, percent=round((count / num_files) * 100, 1)
                    )
                    for kind, count in sorted(
                        kinds.items(), key=lambda x: x[1], reverse=True
                    )
                ]
    final_path = path.resolve() if resolve_path else path
    return DirectoryDetails(
        path=str(final_path),
        num_files=num_files,
        file_types=file_types_by_category,
        subpaths=subpaths,
    )


class FileType(BaseModel):
    type: str
    count: int


class DirectorySummary(BaseModel):
    path: str
    num_files: int
    file_types: List[FileType]
    subpaths: List["DirectorySummary"]


def directory_summary(
    target_path: str,
    ignore_patterns: Optional[Set[str]] = None,
    resolve_path: bool = False,
) -> DirectorySummary:
    """
    Recursively walks a directory and builds a metadata structure for a directory summary.
    This is a simplified version of directory_details that only returns the file types and counts.
    This will adhere to .gitignore files.

    Args:
        target_path: Path to the target directory to analyze
        ignore_patterns: Set of patterns to ignore (applied to all subdirectories)

    Returns:
        DirectorySummary: Pydantic model containing directory structure and file statistics
    """
    path = Path(target_path)
    if not path.is_dir():
        raise ValueError(f"Path {target_path} is not a directory")

    ignore_file = os.path.join(path, ".gitignore")
    ignore_patterns = ignore_patterns or set()
    ignore_patterns = ignore_patterns.union(parse_gitignore(ignore_file))

    # Initialize data structures
    file_types: Dict[str, int] = {}
    subpaths: List[DirectorySummary] = []
    num_files = 0

    # Process directory contents
    for item in path.iterdir():
        # Always ignore .git folders
        if item.name == ".git":
            continue
        # Check if item should be ignored based on ignore_patterns
        if should_ignore_path(item, ignore_patterns, Path(target_path)):
            continue
        if item.is_dir():
            # Recursively process subdirectory with the same ignore_patterns
            sub_metadata = directory_summary(str(item), ignore_patterns, resolve_path)
            subpaths.append(sub_metadata)
        else:
            # Count file and type
            num_files += 1
            file_ext = item.suffix or ".no_ext"
            file_types[file_ext] = file_types.get(file_ext, 0) + 1

    # Convert file types to list of FileType models
    file_types_list = [
        FileType(type=ext, count=count) for ext, count in sorted(file_types.items())
    ]
    final_path = path.resolve() if resolve_path else path
    return DirectorySummary(
        path=str(final_path),
        num_files=num_files,
        file_types=file_types_list,
        subpaths=subpaths,
    )
