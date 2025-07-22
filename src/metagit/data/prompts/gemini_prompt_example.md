## Prompt

create a yaml file named .metagit.example.yml in the root of this project that adheres to the jsonschema file
./schemas/metagit_config.schema.json that is based on the folders and files within this project. Be certain to adhere to
.gitignore when processing files. Only actually read in the file contents for any discovered CICD files, docker image files,
and other files that may have external dependency references. Do your best to infer directory purpose without reading in
everything. For example, tests with several dozen .py files would be unit tests and not valuable. Intelligently trace for
important files and project structure by using the build_files.important list found in ./src/metagit/data/build-files.yaml
as a compass. The end goal will be to create the file as instructed so that it accurately represents the languages, used
frameworks, dependencies, and other project data.

## Tokens Used

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