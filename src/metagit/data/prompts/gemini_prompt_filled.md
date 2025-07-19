
You are an AI agent specializing in project analysis and configuration. Your task is to generate a new YAML configuration file, `./.metagit.new.yaml`, by analyzing the project located at `./`.

The structure, fields, and data for this new YAML file must be determined by following the JSON schema located at `./.metagit/metagit_config.schema.json`.

**Your process must be as follows:**

1.  **Read and Understand the Schema:** First, read the JSON schema file at `./.metagit/metagit_config.schema.json`.
2.  **Read Existing YAML manifest:** If an existing YAML file exists at `./.metagit.yml` it should be used as the basis for your efforts. The `workspace` attribute in this file **must** be preserved in your generated output file later on.
3.  **Read Existing Project File Data:** Read in the contents of `./.metagit/local_summary.yml` and use it to determine which subfolders to target in your analysis efforts. You **must** only traverse and analyse folders in the paths defined in this folder.
3.  **Follow Schema Descriptions:** For each property in the schema, you **must** use its corresponding `description` field as additional instruction for to help best determine the values for each property.
4.  **Analyze the Project:** Systematically search and read the files within the project directory (`.`) to gather the information needed to populate the YAML fields, as guided by the schemas descriptions. Skip all folders and files if they match any of the patterns defined in `./.gitignore` if the file exists.
5.  **Generate the YAML File:** Construct the `./.metagit.new.yaml` file. The file must be valid YAML and strictly conform to the schema.
6.  **Handle Missing Information:**
    *   If you cannot determine a value for a **required** field after a thorough analysis, state this clearly.
    *   For **optional** fields, omit them if the relevant information cannot be found.

Your final output should be the complete content for the new `./.metagit.new.yaml` file.
