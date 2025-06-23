


## Provider Plugins
```mermaid
graph TD
    A[CLI: detect repository] --> B{RepositoryAnalysis};
    B --> C{ProviderManager};
    C --> D{Identifies provider from URL};
    D --> E[Provider Interface];
    C --> F(Load Plugins);
    F --> G[GitHub Plugin];
    F --> H[GitLab Plugin];
    G --> E;
    H --> E;
    B --> E;
    subgraph "providers"
        E
        G
        H
    end
```

Plugin directory structure
```
metagit/
└── providers/
    ├── __init__.py
    ├── base.py          # Defines the base provider interface
    ├── manager.py       # Manages plugin discovery and loading
    ├── github.py        # GitHub provider plugin
    └── gitlab.py        # GitLab provider plugin (for the future)
```