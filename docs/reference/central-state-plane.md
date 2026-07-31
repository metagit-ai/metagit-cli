# Central state plane (RFC-0015)

Metagit’s **central state plane** is a pluggable `DocumentStore` under coordination
services (objectives, handoffs, approvals, events). The same CAS protocol backs
local JSON, today’s HTTP ops API, in-memory tests, and optional cloud stores
(DynamoDB, MongoDB).

Default remains **local** — no behavior change without explicit config or env.
Git stays authoritative for source code; the plane holds coordination documents
(and reserved namespaces for later ACL/catalog migrations).

Related docs:

- [Sharing state (multi-agent)](sharing-state.md) — HTTP ops contract, local paths, agent setup
- [Agent coordination (ACL)](agent-coordination.md) — filesystem ACL today; plane migration is design-only
- Design: [RFC-0015](../superpowers/specs/2026-07-31-rfc-0015-central-state-plane-design.md)
- ACL namespace mapping (no code flip): [ACL migration notes](../superpowers/specs/2026-07-31-rfc-0015-acl-namespace-migration.md)

## Backends

| Backend | Extra | Role |
|---------|-------|------|
| `local` | (none) | Default. Locked JSON under the session/manifest root (legacy `coord.*` paths). |
| `http` | (none) | Client transport to `metagit web serve` `/v3/ops/*` via `METAGIT_STATE_URL`. |
| `memory` | (none) | In-process store for tests; not for production. |
| `dynamodb` | `metagit-cli[state-dynamodb]` | Single-table DynamoDB DocumentStore. |
| `mongodb` | `metagit-cli[state-mongodb]` | MongoDB DocumentStore. |

### Optional extras

```bash
uv tool install 'metagit-cli[state-dynamodb]'
uv tool install 'metagit-cli[state-mongodb]'
# or both:
uv tool install 'metagit-cli[state-dynamodb,state-mongodb]'
```

Cloud SDKs are **not** in the base install. Without the extra, selecting
`dynamodb` / `mongodb` fails with an install hint.

## Identity

Every document key includes `org_id` and `workspace_id`:

| Setting | App config | Environment | Default when empty |
|---------|------------|-------------|--------------------|
| Organization | `state.org_id` | `METAGIT_STATE_ORG_ID` | `_` |
| Workspace | `state.workspace_id` | `METAGIT_STATE_WORKSPACE_ID` | Stable hash of resolved session/manifest root |

Env overrides take precedence over the file. Local backends may ignore `org_id`
for path layout while still reporting it on diagnostics.

## App config

```yaml
# ~/.config/metagit/config.yml
config:
  state:
    backend: local          # local | http | dynamodb | mongodb | memory
    url: ""                 # http only
    token: ""               # http bearer
    conflict_retries: 1
    org_id: ""
    workspace_id: ""
    dynamodb:
      table: ""
      region: ""
      endpoint_url: ""      # LocalStack / dynalite
    mongodb:
      uri: ""
      database: ""
      collection: "metagit_state"
```

### Environment overrides

| Variable | Purpose |
|----------|---------|
| `METAGIT_STATE_BACKEND` | `local` \| `http` \| `dynamodb` \| `mongodb` \| `memory` |
| `METAGIT_STATE_URL` | HTTP ops base (forces http when set) |
| `METAGIT_STATE_TOKEN` | Bearer token for HTTP |
| `METAGIT_STATE_ORG_ID` | Org partition |
| `METAGIT_STATE_WORKSPACE_ID` | Workspace partition |
| `METAGIT_STATE_DDB_TABLE` | DynamoDB table name |
| `METAGIT_STATE_DDB_REGION` | AWS region |
| `METAGIT_STATE_DDB_ENDPOINT` | Optional custom endpoint |
| `METAGIT_STATE_MONGO_URI` | Mongo connection URI |
| `METAGIT_STATE_MONGO_DB` | Database name |

## Deployment shapes

### Deployment A: agents to cloud directly

Each agent host installs the cloud extra and points `state.backend` at DynamoDB
or MongoDB. No ops HTTP hop for coordination documents.

```bash
uv tool install 'metagit-cli[state-dynamodb]'
export METAGIT_AGENT_MODE=true
export METAGIT_STATE_BACKEND=dynamodb
export METAGIT_STATE_ORG_ID=acme
export METAGIT_STATE_WORKSPACE_ID=platform-ws
export METAGIT_STATE_DDB_TABLE=metagit-state
export METAGIT_STATE_DDB_REGION=us-east-1
# AWS credentials via the normal AWS chain (env, profile, IAM role) — never commit them
```

MongoDB shape is the same with `METAGIT_STATE_BACKEND=mongodb`,
`METAGIT_STATE_MONGO_URI`, and `METAGIT_STATE_MONGO_DB`.

### Deployment B: ops server hosts cloud store

Run `metagit web serve` on a coordinator with DynamoDB/Mongo configured
server-side. Agents keep today’s client setup (`METAGIT_STATE_URL` + optional
token); they do **not** need cloud extras.

```bash
# Coordinator host
uv tool install 'metagit-cli[state-dynamodb]'
export METAGIT_STATE_BACKEND=dynamodb
export METAGIT_STATE_DDB_TABLE=metagit-state
export METAGIT_STATE_DDB_REGION=us-east-1
export METAGIT_STATE_ORG_ID=acme
export METAGIT_STATE_WORKSPACE_ID=platform-ws
metagit web serve --host 127.0.0.1 --port 8787

# Every agent host (base install is enough)
export METAGIT_STATE_URL=https://coordinator.example.com:8787
export METAGIT_STATE_TOKEN='…'
```

HTTP clients continue to use whole-document `/v3/ops/*` routes; see
[sharing-state.md](sharing-state.md#http-contract-whole-document-state).

## DynamoDB table bootstrap

Single-table design: partition key `pk`, sort key `sk`.

| Attribute | Role |
|-----------|------|
| `pk` | `ORG#{org_id}#WS#{workspace_id}` |
| `sk` | `NS#{namespace}#KEY#{key}` |
| `body` | JSON string |
| `token` | content hash (CAS) |
| `updated_at` | ISO-8601 |

Create table (CLI):

```bash
aws dynamodb create-table \
  --table-name metagit-state \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE
```

Python equivalent used in tests:

```python
ddb.create_table(
    TableName="metagit-state",
    BillingMode="PAY_PER_REQUEST",
    AttributeDefinitions=[
        {"AttributeName": "pk", "AttributeType": "S"},
        {"AttributeName": "sk", "AttributeType": "S"},
    ],
    KeySchema=[
        {"AttributeName": "pk", "KeyType": "HASH"},
        {"AttributeName": "sk", "KeyType": "RANGE"},
    ],
)
```

Conditional writes enforce CAS (`attribute_not_exists` or matching `token`).

## MongoDB layout

Documents use a compound `_id` of
`{org_id, workspace_id, namespace, key}` plus `body`, `token`, and `updated_at`.
CAS uses `findOneAndUpdate` filtered on `_id` and `token`.

## Diagnostics

`metagit://gate/status` → `state_backend` reports effective backend, `org_id`,
`workspace_id`, whether optional extras are importable, `token_configured`
(boolean only), and which `METAGIT_STATE_*` env vars are set. Secrets are never
returned.

```bash
metagit appconfig show --format json   # includes state block (tokens redacted in preview)
```

## Security

- **Never commit credentials** — AWS keys, Mongo URIs, or bearer tokens do not
  belong in `.metagit.yml`, git, or skills. Use env, IAM roles, or a secrets manager.
- Cloud credentials come from the AWS default chain or Mongo URI env — not the
  workspace manifest.
- Tokens and URIs are redacted in `metagit appconfig preview`.
- Do not bind `metagit web serve` to public interfaces without TLS and auth —
  see [Metagit Web security](metagit-web.md#security).

## Namespaces (MVP)

| Namespace | Domain |
|-----------|--------|
| `coord.objectives` | Objectives envelope |
| `coord.handoffs` | Handoffs |
| `coord.approvals` | Approval queue |
| `coord.events` | Events feed |

Reserved for later (no default flip in RFC-0015): `acl.*`, `task.*`,
`schedule.*`, `merge.*`, `catalog.workspace`, `ontology.*`. See the
[ACL migration notes](../superpowers/specs/2026-07-31-rfc-0015-acl-namespace-migration.md).

## Implementation reference

- Package: `src/metagit/core/state/` (`document.py`, `resolver.py`, adapters, optional `dynamodb.py` / `mongodb.py`)
- Series index: [Central State Plane series](../superpowers/specs/2026-07-31-central-state-plane-series-index.md)
- Bundled skill: **`metagit-sharing-state`**
