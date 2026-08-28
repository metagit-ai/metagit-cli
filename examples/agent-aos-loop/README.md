# Agent AOS loop example

Minimal umbrella workspace that documents the day-1 Agent OS control loop.
See [docs/agents-quickstart.md](../../docs/agents-quickstart.md).

```bash
export METAGIT_AGENT_MODE=true
metagit config validate -c .metagit.yml
metagit context pack --tier 0 --json -c .metagit.yml
metagit prompt workspace --kind session-start --text-only -c .metagit.yml
metagit aos status --json --definition .metagit.yml
metagit aos next --json --definition .metagit.yml
```

Replace the sample repo URL with a real remote (or a local `path:`) before syncing.
Without a task graph, `aos next` may report no ready work — create tasks with
`metagit task create` when you want the scheduler to rank something.
