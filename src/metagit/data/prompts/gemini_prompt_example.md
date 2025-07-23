## Prompt 1

Create a yaml file named .metagit.example.yml in the root of this project that adheres to the jsonschema file
./schemas/metagit_config.schema.json that is based on the folders and files within this project. Be certain to adhere to
.gitignore when processing files. Only actually read in the file contents for any discovered CICD files, docker image files,
and other files that may have external dependency references. Do your best to infer directory purpose without reading in
everything. For example, tests with several dozen .py files would be unit tests and not valuable. Intelligently trace for
important files and project structure by using the build_files.important list found in ./src/metagit/data/build-files.yaml
as a compass. The end goal will be to create the file as instructed so that it accurately represents the languages, used
frameworks, dependencies, and other project data.

╭──────────────────────────────────╮
│                                  │
│  Agent powering down. Goodbye!   │
│                                  │
│                                  │
│  Cumulative Stats (1 Turns)      │
│                                  │
│  Input Tokens           134,416  │
│  Output Tokens            1,607  │
│  Thoughts Tokens          2,186  │
│  ──────────────────────────────  │
│  Total Tokens           138,209  │
│                                  │
│  Total duration (API)     48.1s  │
│  Total duration (wall)  16m 57s  │
│                                  │
╰──────────────────────────────────╯

## Prompt 2

Perform a comprehensive analysis of the files in this project. Update the yaml file named .metagit.example.yml in the root of this project in a manner that adheres to the jsonschema file located at ./schemas/metagit_config.schema.json. Ensure you skip files matching the patterns in .gitignore. Do your best to update even optional elements of this schema. Pay special attention to dependencies found in Dockerfiles, CICD files, and mcp definitions. When complete also create a project.metagit.md file with additional documentation on the project components that includes a mermaid diagram of how they interact.

╭─────────────────────────────────╮
│                                 │
│  Agent powering down. Goodbye!  │
│                                 │
│                                 │
│  Cumulative Stats (1 Turns)     │
│                                 │
│  Input Tokens          134,880  │
│  Output Tokens           2,037  │
│  Thoughts Tokens         1,790  │
│  ─────────────────────────────  │
│  Total Tokens          138,707  │
│                                 │
│  Total duration (API)    49.4s  │
│  Total duration (wall)  2m 26s  │
│                                 │
╰─────────────────────────────────╯

## Prompt 3

You are an expert devops and software engineer. Intelligently explore this project for its use of secrets and variables paying special attention to only those affecting the runtime behavior of the code and the cicd workflows used to release the project's artifacts. Create a report in ./docs/secrets.analysis.md on each of the secrets found and were they are sourced from. Using this data create a yaml file at ./docs/secrets.definitions.yml that represents the secrets, their provenance, and where they should be placed.

## Prompt 4 - Simplified Project Docs

Perform a comprehensive analysis of the files in this project. Update the yaml file named .metagit.example.yml in the root of this project in a manner that adheres to the jsonschema file located at ./schemas/metagit_config.schema.json. Ensure you skip files matching the patterns in .gitignore. Do your best to update even optional elements of this schema. Pay special attention to dependencies found in Dockerfiles, CICD files, and mcp definitions. When complete also create ./docs/app.logic.md with additional documentation on the project components that includes a mermaid diagram of how they interact.