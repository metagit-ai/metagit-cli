#! /usr/bin/env python3
"""
File reader tool for the detect flow
"""
import os
import json
import fnmatch
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional, NamedTuple, Set
from metagit import DATA_PATH

class FileTypeInfo(NamedTuple):
    kind: str
    type: str

class FileTypeWithPercent(NamedTuple):
    kind: str
    percent: float

class DirectoryPathInfo(NamedTuple):
    path: str
    num_files: int
    file_types: Dict[str, List[FileTypeWithPercent]]
    subpaths: List["DirectoryPathInfo"]

class FileExtensionLookup:
    def __init__(self, extension_data: str = os.path.join(DATA_PATH, "file-types.json")):
        # Parse JSON data
        try:
          with open(extension_data, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
        
        # Create extension to info mapping for O(1) lookup
        self._lookup: Dict[str, FileTypeInfo] = {}
        
        # Handle the JSON structure which has data wrapped in "extensions" key
        if isinstance(data, dict) and "extensions" in data:
            items = data["extensions"]
        else:
            items = data
            
        for item in items:
            if isinstance(item, dict):
                kind = item.get('kind', '')
                file_type = item.get('type', '')
                extensions = item.get('extensions', [])
                
                # Store each extension with its corresponding info
                info = FileTypeInfo(kind=kind, type=file_type)
                for ext in extensions:
                    # Normalize extension (lowercase, ensure leading dot)
                    ext = ext.lower()
                    if not ext.startswith('.'):
                        ext = f'.{ext}'
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
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
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
        if fnmatch.fnmatch(relative_str, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        # Handle glob patterns
        elif fnmatch.fnmatch(relative_str, pattern):
            return True
    
    return False

def directory_details(target_path: str, file_lookup: FileExtensionLookup, ignore_patterns: Optional[Set[str]] = None, resolve_path: bool = False) -> DirectoryPathInfo:
    """
    Recursively walks a directory and builds detailed metadata structure using FileExtensionLookup.
    
    Args:
        target_path: Path to the target directory to analyze
        file_lookup: Single instance of FileExtensionLookup for file type information
        ignore_patterns: Set of patterns to ignore (applied to all subdirectories)
        
    Returns:
        DirectoryPathInfo: NamedTuple containing directory structure and detailed file statistics grouped by category
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
        "prose": {}
    }
    subpaths: List[DirectoryPathInfo] = []
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
            sub_metadata = directory_details(str(item), file_lookup, ignore_patterns, resolve_path)
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
                    file_type_counts[category][kind] = file_type_counts[category].get(kind, 0) + 1

    # Convert counts to percentages based on total files in directory
    file_types_by_category: Dict[str, List[FileTypeWithPercent]] = {}
    
    if num_files > 0:  # Only calculate percentages if there are files
        for category, kinds in file_type_counts.items():
            if kinds:  # Only include categories that have files
                file_types_by_category[category] = [
                    FileTypeWithPercent(
                        kind=kind,
                        percent=round((count / num_files) * 100, 1)
                    )
                    for kind, count in sorted(kinds.items(), key=lambda x: x[1], reverse=True)
                ]
    if resolve_path:
        final_path = path.resolve()
    else:
        final_path = path
    return DirectoryPathInfo(
        path=str(final_path),
        num_files=num_files,
        file_types=file_types_by_category,
        subpaths=subpaths
    )

class FileType(BaseModel):
    type: str
    count: int

class DirectoryMetadata(BaseModel):
    path: str
    num_files: int
    file_types: List[FileType]
    subpaths: List["DirectoryMetadata"]

def directory_summary(target_path: str, ignore_patterns: Optional[Set[str]] = None, resolve_path: bool = False) -> DirectoryMetadata:
    """
    Recursively walks a directory and builds a metadata structure.
    
    Args:
        target_path: Path to the target directory to analyze
        ignore_patterns: Set of patterns to ignore (applied to all subdirectories)
        
    Returns:
        DirectoryMetadata: Pydantic model containing directory structure and file statistics
    """
    path = Path(target_path)
    if not path.is_dir():
        raise ValueError(f"Path {target_path} is not a directory")

    # Use provided ignore_patterns or empty set
    ignore_patterns = ignore_patterns or set()

    # Initialize data structures
    file_types: Dict[str, int] = {}
    subpaths: List[DirectoryMetadata] = []
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
    if resolve_path:
        final_path = path.resolve()
    else:
        final_path = path
    return DirectoryMetadata(
        path=str(final_path),
        num_files=num_files,
        file_types=file_types_list,
        subpaths=subpaths
    )


