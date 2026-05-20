import {
  getAppconfigTree,
  getMetagitConfigTree,
  patchAppconfig,
  patchMetagitConfig,
  type ConfigOperation,
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
): Promise<ConfigTreeResponse> {
  return target === 'metagit'
    ? patchMetagitConfig(ops, save)
    : patchAppconfig(ops, save)
}
