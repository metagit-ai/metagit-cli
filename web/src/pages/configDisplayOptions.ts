export type ConfigDisplayOptions = {
  showYamlPreview: boolean
  showUnassigned: boolean
  showListItemHeaders: boolean
  showElementNumbering: boolean
  showTypeLabels: boolean
}

export type SchemaTreeDisplayOptions = Omit<
  ConfigDisplayOptions,
  'showYamlPreview'
>

export const DEFAULT_CONFIG_DISPLAY_OPTIONS: ConfigDisplayOptions = {
  showYamlPreview: false,
  showUnassigned: false,
  showListItemHeaders: false,
  showElementNumbering: false,
  showTypeLabels: false,
}
