# Reading the composed manifest

These commands read the merged manifest through `metagit.manifest.load_composed`. A split layout and its single-file original return the same records. `source` is the only field that changes: it is the fragment path relative to the manifest directory (`.metagit.yml` when the record lives in the root file).

```bash
metagit repo list --all --json -c .metagit.yml
metagit graph nodes --json -c .metagit.yml
metagit graph relationships --json -c .metagit.yml
```

`repo list --all --json` objects use these keys:

| Key | Meaning |
|-----|---------|
| `project` | Workspace project name |
| `name` | Repository name |
| `url` | Clone URL, or JSON `null` when the repo is path-only |
| `kind` | `tags.kind` when that tag is set, otherwise JSON `null` |
| `source` | Fragment path that declared the project |

`graph nodes --json` and `graph relationships --json` return the composed YAML objects plus `source`. Relationship endpoints keep the key that was written (`from` or `from_endpoint`).
