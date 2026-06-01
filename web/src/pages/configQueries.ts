import {
  getAppconfigTree,
  getMetagitConfigTree,
  patchAppconfig,
  patchMetagitConfig,
  postConfigPreview,
  type ConfigOperation,
  type ConfigPreviewResponse,
  type ConfigPreviewStyle,
  type ConfigTreeResponse,
} from '../api/client'

export type ConfigTarget = 'metagit' | 'appconfig'

export const configTreeQueryKey = (target: ConfigTarget) =>
  ['config-tree', target] as const

export function fetchConfigTree(target: ConfigTarget): Promise<ConfigTreeResponse> {
  return target === 'metagit' ? getMetagitConfigTree() : getAppconfigTree()
}

export function patchConfigTree(
  target: ConfigTarget,
  ops: ConfigOperation[],
  save: boolean,
  autoFormat = true,
): Promise<ConfigTreeResponse> {
  return target === 'metagit'
    ? patchMetagitConfig(ops, save, autoFormat)
    : patchAppconfig(ops, save, autoFormat)
}

export function fetchConfigPreview(
  target: ConfigTarget,
  style: ConfigPreviewStyle,
  operations: ConfigOperation[],
): Promise<ConfigPreviewResponse> {
  return postConfigPreview(target, style, operations)
}
