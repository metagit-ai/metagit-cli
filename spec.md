# **RFC-0007: Agent Coordination Layer (ACL)**

**Status:** Draft

**Project:** Metagit

**Author:** Zachary Loeber

***

# **Vision**

Metagit currently serves as an AI-aware catalog and orchestration layer across many repositories.

This RFC expands Metagit into an **Agent Coordination Layer** capable of safely orchestrating hundreds or thousands of concurrent AI agents working across many repositories without interfering with one another.

The goal is to make Git repositories behave more like a distributed operating system for autonomous software agents.

***

# **Problem Statement**

Traditional Git workflows assume:

* One developer
* One working directory
* One feature branch
* Human coordination

Agentic development completely changes these assumptions.

An orchestrator may launch dozens of specialized agents simultaneously.

Those agents may:

* modify multiple repositories
* depend upon one another
* modify overlapping files
* modify the same subsystem
* require shared context
* produce merge conflicts

Git provides no primitives for:

* branch ownership
* repository leases
* file ownership
* task ownership
* dependency tracking
* automatic conflict avoidance
* branch lifecycle management

Metagit should become the coordination layer that provides these capabilities.

***

# **Core Principles**

## **1. Agents Never Share Worktrees**

Every agent receives its own Git worktree.

Never allow two agents to modify the same checkout.

Example

```
workspace/

    metagit/

    repos/

        service-a/

        service-b/

    .worktrees/

        agent-001/

        agent-002/

        agent-003/
```

Each worktree maps to exactly one active task.

***

## **2. Agents Never Share Branches**

Branches become disposable execution environments.

Naming convention

```
agent/<task-id>

agent/<uuid>

agent/<task-id>-<short-description>
```

Examples

```
agent/412-route53-cleanup

agent/413-auth-refactor

agent/414-add-tests
```

Feature branches become integration targets instead of working branches.

```
feature/auth

    ↑

agent/412

agent/413

agent/414
```

***

## **3. Branch Leasing**

Introduce a lease manager.

A lease represents temporary ownership.

Example

```
Lease

Repository:
    auth-service

Branch:
    agent/412

Owner:
    agent-412

Task:
    Add JWT refresh support

Expiration:
    2026-07-08T20:00Z
```

Agents cannot acquire an already leased branch.

Leases automatically expire.

The orchestrator may renew them.

***

## **4. Repository Locking**

Repository locking should be advisory rather than exclusive.

Multiple agents may work in the same repository provided they do not conflict.

Metagit tracks active agents per repository.

```
Repository

auth-service

Agents

412

418

429

441
```

***

# **File Reservation System**

Prior to coding an agent declares intended modifications.

Example

```
claims:

- backend/auth/*
- backend/token/*
```

The orchestrator records claims.

New agents attempting overlapping claims receive:

```
Conflict

Owner:
    agent-412

Files:

backend/auth/*
```

Possible actions

* wait
* subdivide task
* negotiate ownership
* spawn merge agent
* override manually

Claims are advisory.

Git remains the final authority.

***

# **Semantic Ownership**

Future versions should reserve concepts rather than files.

Examples

```
Authentication

Billing

Terraform

Networking

GraphQL

Caching
```

Metagit’s repository knowledge graph determines likely ownership.

This allows conflict detection before editing begins.

***

# **Worktree Manager**

New component

```
metagit worktree create

metagit worktree destroy

metagit worktree gc

metagit worktree status
```

Responsibilities

* create isolated directories
* fetch latest branch
* configure remotes
* inject agent metadata
* configure sparse checkout (future)

***

# **Branch Manager**

Commands

```
metagit branch allocate

metagit branch release

metagit branch cleanup

metagit branch archive
```

Responsibilities

* unique naming
* ownership tracking
* automatic deletion
* stale detection

***

# **Lease Manager**

Commands

```
metagit lease acquire

metagit lease renew

metagit lease release

metagit lease list
```

Lease metadata

```
lease-id

branch

repository

agent-id

task-id

created

expires

status
```

***

# **Task Graph**

Metagit should internally represent work as a DAG.

Example

```
Implement Authentication

├── Create JWT middleware

├── Update login endpoint

├── Add frontend login

└── Integration tests
```

Each node becomes independently executable.

Each node may own:

* branch
* worktree
* lease
* context
* dependencies

Completion automatically unlocks downstream nodes.

***

# **Agent Manifest**

Every agent receives a manifest.

Example

```
agent_id

task_id

branch

worktree

repositories

claims

dependencies

integration_branch

context_budget

completion_requirements
```

This becomes the canonical execution contract.

***

# **Context Isolation**

Agents should receive the minimum context necessary.

Context hierarchy

```
Global

↓

Workspace

↓

Repository

↓

Directory

↓

Task

↓

File
```

Metagit computes the minimum viable context.

Benefits

* lower token cost
* improved reasoning
* reduced hallucination

***

# **Integration Branches**

Never merge directly into feature branches.

Instead

```
feature/auth

↓

integration/auth
```

Agents merge into integration.

Integration continuously validates

* build
* lint
* tests
* policy
* security

Only after validation succeeds does integration merge into feature.

***

# **Merge Orchestrator**

New subsystem.

Responsibilities

* merge completed agent branches
* detect conflicts
* launch merge-resolution agents
* retry merges
* validate build
* notify orchestrator

This effectively becomes CI for autonomous agents.

***

# **Event Bus**

Every lifecycle event becomes observable.

Examples

```
AgentStarted

LeaseGranted

LeaseExpired

BranchAllocated

BranchReleased

ConflictDetected

MergeSucceeded

MergeFailed

TaskCompleted

TaskBlocked
```

Future integrations

* MCP
* LangGraph
* CrewAI
* OpenTelemetry
* Grafana

***

# **Persistence**

State should survive orchestrator restarts.

Possible storage

```
.metagit/

    agents/

    leases/

    tasks/

    worktrees/

    branches/

    graph/

    events/
```

Long-term

SQLite

or

Postgres

should replace flat files.

***

# **Scheduling**

Future scheduler responsibilities

* priority
* dependency ordering
* repository affinity
* context reuse
* GPU availability
* model selection
* estimated token cost
* estimated runtime

The scheduler chooses which task executes next.

***

# **Long-Term Vision**

Git tracks commits.

Metagit should track **intent**.

Instead of asking:

“What changed?”

Metagit answers:

“Why was this change made?”

The repository evolves from a version history into a living knowledge graph describing goals, dependencies, ownership, context, and autonomous execution.

Git remains the source of truth for code.

Metagit becomes the operating system that coordinates autonomous software development across repositories, agents, and organizations.


# **Development Plan**

We will be splitting this into a series of RFCs rather than implementing it all at once:

- **RFC-0007:** Agent Coordination Layer (this document)
- **RFC-0008:** Task Graph & Intent Engine
- **RFC-0009:** Agent Context Compiler
- **RFC-0010:** Semantic Repository Knowledge Graph
- **RFC-0011:** Merge Orchestrator & Conflict Resolution
- **RFC-0012:** Distributed Agent Scheduler
- **RFC-0013:** Agent Operating System (AOS)

That progression naturally evolves Metagit from a repository catalog into a true operating system for autonomous software development, with each RFC building on the primitives introduced by the previous one.