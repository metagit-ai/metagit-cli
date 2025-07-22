# Metagit Terminology

IT has a way with words doesn't it? This is a short list of metagit terms and their concise meaning to reduce confusion.

**Path (aka. Target)** - A folder within a git repository.

**Repo** - A git repository. If it happens to be a monorepo there maybe several targets within the repository with unique associated metadata.

**Project** - A collection of git repositories. In VSCode this is a workspace. We define a project at this higher level than the repository because we want a more holistic view of what your code entails as a whole. While a repo maybe produces a single app it may have several internal/external dependencies that make up the whole of what it requires to deploy it.

**Workspace** - A collection of projects. Fundamentally different than a VSCode workspace. For metagit the most important thing to understand is that this is the target folder where all projects and their repos will be cloned/copied into.

This creates a hierarchy like the following:

```
Workspace/
└── ProjectA/
    └── RepoA1/
        ├── Path1
        └── Path2
    └── RepoA2/
        └── Path1
└── ProjectB/
    └── RepoB1/
        ├── Path1
        └── Path2
    └── RepoB2/
      └── Path1
```

> **NOTE** It is entirely possible to have the same repo referenced in multiple projects. Local paths defined this way will simply be soft links. Multiple project repositories defined this way will be treated independently.
