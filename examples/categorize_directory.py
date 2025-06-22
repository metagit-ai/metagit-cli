#!/usr/bin/env python3
"""
Example script to categorize directory contents using metagit utilities.

This script demonstrates how to use the directory_summary and directory_details
functions to analyze directory structure and output the results in YAML format.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import metagit modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import yaml

from metagit.core.utils.files import (
    directory_summary,
    directory_details,
    FileExtensionLookup
)


def convert_namedtuple_to_dict(obj):
    """Convert NamedTuple objects to dictionaries for YAML serialization."""
    if hasattr(obj, '_asdict'):
        # Handle NamedTuple
        result = obj._asdict()
        # Recursively convert nested NamedTuples
        for key, value in result.items():
            if isinstance(value, list):
                result[key] = [convert_namedtuple_to_dict(item) for item in value]
            elif hasattr(value, '_asdict'):
                result[key] = convert_namedtuple_to_dict(value)
            elif isinstance(value, dict):
                # Handle nested dictionaries (like file_types)
                result[key] = {k: convert_namedtuple_to_dict(v) for k, v in value.items()}
        return result
    elif isinstance(obj, list):
        return [convert_namedtuple_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_namedtuple_to_dict(v) for k, v in obj.items()}
    else:
        return obj


@click.command()
@click.option(
    '--path',
    '-p',
    default='.',
    help='Path to the directory to analyze (defaults to current directory)'
)
@click.option(
    '--output-type',
    '-o',
    type=click.Choice(['summary', 'details']),
    default='summary',
    help='Type of output: summary (DirectoryMetadata) or details (DirectoryPathInfo)'
)
@click.option(
    '--output-file',
    '-f',
    help='Output file path (if not specified, prints to stdout)'
)
def categorize_directory(path: str, output_type: str, output_file: str):
    """
    Categorize directory contents and output in YAML format.
    
    This script analyzes a directory structure and provides either a summary
    (file counts by extension) or detailed analysis (file types with names and categories).
    """
    try:
        # Validate the path
        target_path = Path(path)
        if not target_path.exists():
            click.echo(f"Error: Path '{path}' does not exist.", err=True)
            sys.exit(1)
        
        if not target_path.is_dir():
            click.echo(f"Error: Path '{path}' is not a directory.", err=True)
            sys.exit(1)
        
        click.echo(f"Analyzing directory: {target_path}")
        
        # Generate the appropriate output based on type
        if output_type == 'summary':
            result = directory_summary(str(target_path))
            # Convert Pydantic model to dict for YAML serialization
            output_data = result.model_dump()
        else:  # details
            file_lookup = FileExtensionLookup()
            result = directory_details(str(target_path), file_lookup)
            # Convert NamedTuple to dict for YAML serialization
            output_data = convert_namedtuple_to_dict(result)
        
        # Convert to YAML
        yaml_output = yaml.dump(output_data, default_flow_style=False, indent=2, sort_keys=False)
        
        # Output the result
        if output_file:
            with open(output_file, 'w') as f:
                f.write(yaml_output)
            click.echo(f"Output written to: {output_file}")
        else:
            click.echo("Directory Analysis Results:")
            click.echo("=" * 50)
            click.echo(yaml_output)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    categorize_directory()
