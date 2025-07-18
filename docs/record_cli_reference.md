# Record Management CLI Reference

The `metagit record` command group provides comprehensive record management functionality using the `MetagitRecordManager` with support for multiple storage backends.

## Overview

The record management system allows you to:
- Create records from existing metagit configuration files
- Store records in local files or OpenSearch
- Search, update, and delete records
- Export and import records
- View statistics and analytics

## Storage Backends

### Local File Storage (Default)
Records are stored as JSON files in a local directory with an index file for quick lookups.

### OpenSearch Storage
Records are stored in an OpenSearch index for scalable, searchable storage.

## Command Reference

### Global Options

All record commands support these global options:

- `--storage-type`: Storage backend type (`local` or `opensearch`)
- `--storage-path`: Path for local storage (default: `./records`)
- `--opensearch-hosts`: OpenSearch hosts (comma-separated, default: `localhost:9200`)
- `--opensearch-index`: OpenSearch index name (default: `metagit-records`)
- `--opensearch-username`: OpenSearch username
- `--opensearch-password`: OpenSearch password
- `--opensearch-use-ssl`: Use SSL for OpenSearch connection

### Commands

#### `metagit record create`

Create a record from a metagit configuration file.

**Options:**
- `--config-path`: Path to the metagit configuration file (default: `.metagit.yml`)
- `--detection-source`: Source of the detection (default: `local`)
- `--detection-version`: Version of the detection system (default: `1.0.0`)
- `--output-file`: Save record to file (optional)

**Examples:**
```bash
# Create a record from the current directory's .metagit.yml
metagit record create

# Create a record with custom detection source
metagit record create --detection-source github --detection-version 2.0.0

# Create a record and save to file
metagit record create --output-file my-record.yml
```

#### `metagit record show`

Show record(s) in various formats.

**Arguments:**
- `record_id`: Optional record ID to show specific record

**Options:**
- `--format`: Output format (`yaml` or `json`, default: `yaml`)

**Examples:**
```bash
# List all records
metagit record show

# Show specific record
metagit record show 1

# Show record in JSON format
metagit record show 1 --format json
```

#### `metagit record search`

Search records with optional filters and pagination.

**Arguments:**
- `query`: Search query string

**Options:**
- `--page`: Page number for pagination (default: 1)
- `--size`: Number of records per page (default: 20)
- `--format`: Output format (`yaml`, `json`, or `table`, default: `table`)

**Examples:**
```bash
# Search for records containing "python"
metagit record search python

# Search with pagination
metagit record search web --page 2 --size 10

# Search with YAML output
metagit record search api --format yaml
```

#### `metagit record update`

Update an existing record.

**Arguments:**
- `record_id`: ID of the record to update

**Options:**
- `--config-path`: Path to the updated metagit configuration file (default: `.metagit.yml`)
- `--detection-source`: Updated detection source
- `--detection-version`: Updated detection version

**Examples:**
```bash
# Update record with new config file
metagit record update 1 --config-path updated-config.yml

# Update only detection source
metagit record update 1 --detection-source github
```

#### `metagit record delete`

Delete a record.

**Arguments:**
- `record_id`: ID of the record to delete

**Options:**
- `--force`: Force deletion without confirmation

**Examples:**
```bash
# Delete with confirmation
metagit record delete 1

# Force delete without confirmation
metagit record delete 1 --force
```

#### `metagit record export`

Export a record to file.

**Arguments:**
- `record_id`: ID of the record to export
- `output_file`: Output file path

**Options:**
- `--format`: Export format (`yaml` or `json`, default: `yaml`)

**Examples:**
```bash
# Export record to YAML
metagit record export 1 my-record.yml

# Export record to JSON
metagit record export 1 my-record.json --format json
```

#### `metagit record import`

Import a record from file.

**Arguments:**
- `input_file`: Input file path

**Options:**
- `--detection-source`: Override detection source
- `--detection-version`: Override detection version

**Examples:**
```bash
# Import record from file
metagit record import my-record.yml

# Import with custom detection source
metagit record import my-record.yml --detection-source imported --detection-version 2.0.0
```

#### `metagit record stats`

Show record storage statistics.

**Examples:**
```bash
# Show statistics
metagit record stats
```

## Usage Examples

### Basic Workflow

1. **Create a record from configuration:**
   ```bash
   metagit record create --config-path .metagit.yml
   ```

2. **List all records:**
   ```bash
   metagit record show
   ```

3. **Search for specific records:**
   ```bash
   metagit record search python --format table
   ```

4. **Update a record:**
   ```bash
   metagit record update 1 --detection-source github
   ```

5. **Export a record:**
   ```bash
   metagit record export 1 exported-record.yml
   ```

### Using OpenSearch Backend

```bash
# Create record using OpenSearch storage
metagit record --storage-type opensearch \
  --opensearch-hosts "localhost:9200" \
  --opensearch-index "metagit-records" \
  create

# Search records in OpenSearch
metagit record --storage-type opensearch search "api"
```

### Using Local Storage with Custom Path

```bash
# Use custom local storage path
metagit record --storage-path /path/to/records create

# List records from custom path
metagit record --storage-path /path/to/records show
```

## Error Handling

The record commands provide detailed error messages for common issues:

- **Missing configuration file**: Use `--config-path` to specify the correct path
- **OpenSearch connection issues**: Check host, port, and authentication settings
- **Permission errors**: Ensure write access to storage directories
- **Invalid record ID**: Use `metagit record show` to list valid record IDs

## Integration with Existing Workflows

The record management system integrates seamlessly with existing metagit workflows:

1. **Detection Pipeline**: Records can be created automatically during detection
2. **Configuration Management**: Records are created from existing `.metagit.yml` files
3. **CI/CD Integration**: Records can be exported/imported for deployment tracking
4. **Analytics**: Statistics provide insights into project patterns and trends

## Best Practices

1. **Use descriptive detection sources**: Use meaningful values like `github`, `gitlab`, `local`, `ci-pipeline`
2. **Version your detection system**: Track detection algorithm versions for reproducibility
3. **Regular backups**: Export important records to files for backup
4. **Consistent naming**: Use consistent project names and descriptions
5. **Monitor storage**: Use `metagit record stats` to monitor record growth

## Troubleshooting

### Common Issues

1. **"No storage backend configured"**: Ensure you're using a valid storage type
2. **"Record not found"**: Check the record ID with `metagit record show`
3. **"OpenSearch connection failed"**: Verify OpenSearch is running and accessible
4. **"Permission denied"**: Check file/directory permissions for local storage

### Debug Mode

Enable debug mode for detailed logging:

```bash
metagit --debug record show
```

### Verbose Output

Enable verbose output for more information:

```bash
metagit --verbose record create
``` 