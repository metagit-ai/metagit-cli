import os
import shutil
import click

EXCLUDE_DIRS = {'node_modules', '.venv', 'venv'}

@click.command()
@click.argument('target_dir', type=click.Path(exists=True, file_okay=False))
@click.option('--dry-run', is_flag=True, help="If set, will not delete directories but will show what would be deleted.")
@click.option('--force', is_flag=True, help="If set, will not prompt for confirmation before deleting directories.")
@click.pass_context
def clean_cached(ctx, target_dir, dry_run, force):
    """
    Recursively search TARGET_DIR for node_modules, .venv, and venv folders and delete them.
    """
    deleted = []
    for root, dirs, files in os.walk(target_dir):
        # Make a copy of dirs to iterate over since we may modify dirs in-place
        for d in list(dirs):
            if d in EXCLUDE_DIRS:
                dir_path = os.path.join(root, d)
                try:
                    if not os.path.exists(dir_path):
                        click.echo(f"Directory {dir_path} does not exist, skipping.", err=True)
                        continue
                    if dry_run:
                        click.echo(f"Would delete: {dir_path}")
                        # Remove from dirs so os.walk does not descend into it
                        dirs.remove(d)
                        continue
                    if not force:
                        if not click.confirm(f"Do you really want to delete {dir_path}? [y/N]", abort=True):
                            # Remove from dirs so os.walk does not descend into it
                            dirs.remove(d)
                            continue
                    shutil.rmtree(dir_path)
                    deleted.append(dir_path)
                    click.echo(f"Deleted: {dir_path}")
                except Exception as e:
                    click.echo(f"Failed to delete {dir_path}: {e}", err=True)
                # Always remove from dirs so os.walk does not descend into it
                if d in dirs:
                    dirs.remove(d)
    if not deleted and not dry_run:
        click.echo("No matching directories found.")

if __name__ == '__main__':
    clean_cached()