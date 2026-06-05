---
name: api
description: "Skill for the Api area of metagit-cli. 21 symbols across 6 files."
metadata:
  internal: true
---
# Api

21 symbols | 6 files | Cohesion: 75%

## When to Use

- Working with code in `src/`
- Understanding how do_GET, do_POST, do_DELETE work
- Modifying api-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/api/server.py` | _parse_tag_filters_from_query, _first, do_GET, do_POST, do_DELETE (+1) |
| `src/metagit/core/api/layout_handler.py` | handle, _layout_flags, _bool_param, _load_config, _respond_layout (+1) |
| `src/metagit/core/api/catalog_handler.py` | handle, _load_config, _parse_body, _respond_mutation, _first |
| `web/src/api/client.ts` | patchMetagitConfig, patchAppconfig |
| `web/src/pages/configQueries.ts` | patchConfigTree |
| `web/src/components/SchemaTree.tsx` | SchemaTree |

## Entry Points

Start here when exploring this area:

- **`do_GET`** (Function) — `src/metagit/core/api/server.py:64`
- **`do_POST`** (Function) — `src/metagit/core/api/server.py:157`
- **`do_DELETE`** (Function) — `src/metagit/core/api/server.py:170`
- **`handle`** (Function) — `src/metagit/core/api/catalog_handler.py:29`
- **`handle`** (Function) — `src/metagit/core/api/layout_handler.py:28`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `do_GET` | Function | `src/metagit/core/api/server.py` | 64 |
| `do_POST` | Function | `src/metagit/core/api/server.py` | 157 |
| `do_DELETE` | Function | `src/metagit/core/api/server.py` | 170 |
| `handle` | Function | `src/metagit/core/api/catalog_handler.py` | 29 |
| `handle` | Function | `src/metagit/core/api/layout_handler.py` | 28 |
| `patchConfigTree` | Function | `web/src/pages/configQueries.ts` | 21 |
| `SchemaTree` | Function | `web/src/components/SchemaTree.tsx` | 30 |
| `patchMetagitConfig` | Function | `web/src/api/client.ts` | 116 |
| `patchAppconfig` | Function | `web/src/api/client.ts` | 126 |
| `_parse_tag_filters_from_query` | Function | `src/metagit/core/api/server.py` | 18 |
| `_first` | Function | `src/metagit/core/api/server.py` | 32 |
| `_json` | Function | `src/metagit/core/api/server.py` | 179 |
| `_load_config` | Function | `src/metagit/core/api/catalog_handler.py` | 150 |
| `_parse_body` | Function | `src/metagit/core/api/catalog_handler.py` | 164 |
| `_respond_mutation` | Function | `src/metagit/core/api/catalog_handler.py` | 196 |
| `_first` | Function | `src/metagit/core/api/catalog_handler.py` | 213 |
| `_layout_flags` | Function | `src/metagit/core/api/layout_handler.py` | 154 |
| `_bool_param` | Function | `src/metagit/core/api/layout_handler.py` | 187 |
| `_load_config` | Function | `src/metagit/core/api/layout_handler.py` | 203 |
| `_respond_layout` | Function | `src/metagit/core/api/layout_handler.py` | 217 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `SchemaTree → ApiError` | cross_community | 5 |
| `Do_POST → Load_config` | cross_community | 4 |
| `Do_POST → _bool_param` | cross_community | 4 |
| `Do_DELETE → Load_config` | cross_community | 4 |
| `Do_POST → _first` | cross_community | 3 |
| `Do_POST → _respond_layout` | cross_community | 3 |
| `Do_POST → _parse_body` | intra_community | 3 |
| `Do_POST → _respond_mutation` | intra_community | 3 |
| `Do_DELETE → _parse_body` | intra_community | 3 |
| `Do_DELETE → _respond_mutation` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 4 calls |
| Pages | 3 calls |
| Project | 1 calls |

## How to Explore

1. `gitnexus_context({name: "do_GET"})` — see callers and callees
2. `gitnexus_query({query: "api"})` — find related execution flows
3. Read key files listed above for implementation details
