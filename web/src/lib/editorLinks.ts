export type EditorProtocol = 'vscode' | 'cursor'

export function editorProtocolUrl(
  protocol: EditorProtocol,
  absolutePath: string,
): string {
  const normalized = absolutePath.replace(/\\/g, '/')
  return `${protocol}://file/${normalized}`
}

export const EDITOR_ACTIONS: Array<{
  id: EditorProtocol | 'server'
  label: string
  title: string
}> = [
  {
    id: 'vscode',
    label: 'VS Code',
    title: 'Open in Visual Studio Code',
  },
  {
    id: 'cursor',
    label: 'Cursor',
    title: 'Open in Cursor',
  },
  {
    id: 'server',
    label: 'Default',
    title: 'Open using the configured CLI editor (metagit app config)',
  },
]
