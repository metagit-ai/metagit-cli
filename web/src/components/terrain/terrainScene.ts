import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type {
  RepositoryTerrainNode,
  RepositoryTerrainResponse,
  TerrainDependency,
} from '../../api/client'
import { DEFAULT_LAYERS, type TerrainLayerState } from './terrainLayers'
import {
  createSimpleTileMaterial,
  createTerrainTileMaterial,
  setTileWorkingTreeAttributes,
  setTileWorkingTreeEnabled,
  updateTileMaterialTime,
  type TerrainTileMaterial,
} from './terrainTileMaterial'
import {
  DEFAULT_VIEW_OPTIONS,
  layoutUsesFlatGround,
  resolveTerrainLayout,
  sortTerrainNodes,
  type TerrainLayoutSlot,
  type TerrainViewOptions,
} from './terrainViewOptions'

export { DEFAULT_LAYERS, type TerrainLayerState }
export { DEFAULT_VIEW_OPTIONS, type TerrainViewOptions }

type TerrainVisualPreferences = TerrainViewOptions['visual']

const SYNC_COLORS: Record<string, THREE.Color> = {
  deep_red: new THREE.Color(0xb91c1c),
  orange: new THREE.Color(0xea580c),
  neutral_blue: new THREE.Color(0x3b82f6),
  green: new THREE.Color(0x22c55e),
  bright_green: new THREE.Color(0x84cc16),
  gray: new THREE.Color(0x64748b),
}

const PIPELINE_COLORS: Record<string, THREE.Color> = {
  passed: new THREE.Color(0x22c55e),
  failed: new THREE.Color(0xef4444),
  running: new THREE.Color(0x3b82f6),
  pending: new THREE.Color(0xeab308),
  canceled: new THREE.Color(0x94a3b8),
  skipped: new THREE.Color(0x94a3b8),
  unknown: new THREE.Color(0x64748b),
}

const BRANCH_BORDER_COLORS: Record<string, THREE.Color> = {
  feature: new THREE.Color(0x06b6d4),
  develop: new THREE.Color(0xa855f7),
  hotfix: new THREE.Color(0xf59e0b),
  detached: new THREE.Color(0xf8fafc),
  other: new THREE.Color(0x94a3b8),
}

const OWNERSHIP_PALETTE = [
  0x6366f1, 0x14b8a6, 0xf97316, 0xec4899, 0x8b5cf6, 0x10b981,
]

export interface TerrainSceneCallbacks {
  onSelect: (node: RepositoryTerrainNode | null) => void
  onHover: (node: RepositoryTerrainNode | null, x: number, y: number) => void
}

interface SceneObjects {
  tiles: THREE.InstancedMesh
  tileMaterial: THREE.MeshStandardMaterial | TerrainTileMaterial
  borders: THREE.InstancedMesh
  beacons: THREE.InstancedMesh
  dependencyLines: THREE.LineSegments
  regionOutlines: THREE.LineSegments
  agentMarkers: THREE.InstancedMesh
}

function ownershipColor(owner: string | null | undefined): THREE.Color {
  if (!owner) {
    return new THREE.Color(0x334155)
  }
  let hash = 0
  for (let index = 0; index < owner.length; index += 1) {
    hash = (hash * 31 + owner.charCodeAt(index)) >>> 0
  }
  return new THREE.Color(OWNERSHIP_PALETTE[hash % OWNERSHIP_PALETTE.length] ?? 0x6366f1)
}

function tileHeight(
  node: RepositoryTerrainNode,
  layers: TerrainLayerState,
  visual: TerrainVisualPreferences,
): number {
  const base = visual.style === 'solid' ? 0.42 : 0.35
  if (!layers.terrain || visual.style === 'solid') {
    return base
  }
  return base + Math.max(0.15, node.visual.elevation + 0.35)
}

function tileColor(
  node: RepositoryTerrainNode,
  layers: TerrainLayerState,
  visual: TerrainVisualPreferences,
): THREE.Color {
  if (layers.ownership && node.ownership) {
    return ownershipColor(node.ownership)
  }
  if (!layers.gitState) {
    return SYNC_COLORS.gray.clone()
  }
  const base = SYNC_COLORS[node.visual.sync_color]?.clone() ?? SYNC_COLORS.gray.clone()
  if (visual.style === 'solid') {
    return base
  }
  if (layers.workingTree && node.git.dirty) {
    base.lerp(new THREE.Color(0x1e293b), 0.15)
  }
  const darken = node.visual.darken_factor
  const fade = node.visual.fade_factor
  if (darken > 0 || fade > 0) {
    base.lerp(new THREE.Color(0x0f172a), Math.min(0.85, darken + fade * 0.5))
  }
  return base
}

const _up = new THREE.Vector3(0, 1, 0)
const _normal = new THREE.Vector3()

function placeTileOnSlot(
  dummy: THREE.Object3D,
  slot: TerrainLayoutSlot,
  height: number,
  sphereLayout: boolean,
): void {
  if (sphereLayout) {
    _normal.set(slot.normalX, slot.normalY, slot.normalZ)
    dummy.position.set(
      slot.x + _normal.x * height * 0.5,
      slot.y + _normal.y * height * 0.5,
      slot.z + _normal.z * height * 0.5,
    )
    dummy.quaternion.setFromUnitVectors(_up, _normal)
  } else {
    dummy.position.set(slot.x, height / 2, slot.z)
    dummy.quaternion.set(0, 0, 0, 1)
  }
  dummy.scale.set(1, height, 1)
  dummy.updateMatrix()
}

export class RepositoryTerrainScene {
  readonly domElement: HTMLCanvasElement

  private readonly scene: THREE.Scene
  private readonly camera: THREE.PerspectiveCamera
  private readonly renderer: THREE.WebGLRenderer
  private readonly controls: OrbitControls
  private readonly raycaster = new THREE.Raycaster()
  private readonly pointer = new THREE.Vector2()
  private readonly callbacks: TerrainSceneCallbacks
  private objects: SceneObjects | null = null
  private nodes: RepositoryTerrainNode[] = []
  private dependencies: TerrainDependency[] = []
  private layoutSlots: TerrainLayoutSlot[] = []
  private layers: TerrainLayerState = { ...DEFAULT_LAYERS }
  private viewOptions: TerrainViewOptions = { ...DEFAULT_VIEW_OPTIONS, layout: { ...DEFAULT_VIEW_OPTIONS.layout }, visual: { ...DEFAULT_VIEW_OPTIONS.visual } }
  private readonly ground: THREE.Mesh
  private animationId = 0
  private hoveredId: string | null = null
  private clock = new THREE.Clock()

  constructor(container: HTMLElement, callbacks: TerrainSceneCallbacks) {
    this.callbacks = callbacks
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0x0b1220)
    this.scene.fog = new THREE.Fog(0x0b1220, 40, 220)

    const width = container.clientWidth
    const height = container.clientHeight
    this.camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 500)
    this.camera.position.set(18, 28, 36)

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setSize(width, height)
    container.appendChild(this.renderer.domElement)
    this.domElement = this.renderer.domElement

    this.controls = new OrbitControls(this.camera, this.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.06
    this.controls.maxPolarAngle = Math.PI / 2.05
    this.controls.minDistance = 6
    this.controls.maxDistance = 160

    const ambient = new THREE.AmbientLight(0xbfd7ff, 0.55)
    const sun = new THREE.DirectionalLight(0xffffff, 1.05)
    sun.position.set(30, 50, 20)
    const fill = new THREE.DirectionalLight(0x6366f1, 0.35)
    fill.position.set(-20, 12, -16)
    this.scene.add(ambient, sun, fill)

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(400, 400),
      new THREE.MeshStandardMaterial({
        color: 0x0f172a,
        roughness: 1,
        metalness: 0,
      }),
    )
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.02
    ground.receiveShadow = true
    this.ground = ground
    this.scene.add(ground)

    this.domElement.addEventListener('pointermove', this.onPointerMove)
    this.domElement.addEventListener('pointerdown', this.onPointerDown)
    window.addEventListener('resize', this.onResize)
    this.animate()
  }

  setLayers(layers: TerrainLayerState): void {
    this.layers = { ...layers }
    if (this.nodes.length > 0) {
      this.rebuildMeshes(this.nodes, this.dependencies)
    }
  }

  setViewOptions(options: TerrainViewOptions): void {
    this.viewOptions = {
      layout: { ...options.layout },
      visual: { ...options.visual },
    }
    if (this.nodes.length > 0) {
      this.layoutSlots = resolveTerrainLayout(this.nodes, this.viewOptions.layout)
      this.rebuildMeshes(this.nodes, this.dependencies)
      this.applySceneMode()
      this.fitCamera(this.nodes)
    } else {
      this.applySceneMode()
    }
  }

  setData(data: RepositoryTerrainResponse): void {
    this.nodes = sortTerrainNodes(data.nodes)
    this.dependencies = data.dependencies
    this.layoutSlots = resolveTerrainLayout(this.nodes, this.viewOptions.layout)
    this.rebuildMeshes(this.nodes, data.dependencies)
    this.applySceneMode()
    this.fitCamera(this.nodes)
  }

  highlightNode(_nodeId: string | null): void {
    // Reserved for dependency shockwave / external selection hooks.
  }

  dispose(): void {
    cancelAnimationFrame(this.animationId)
    this.domElement.removeEventListener('pointermove', this.onPointerMove)
    this.domElement.removeEventListener('pointerdown', this.onPointerDown)
    window.removeEventListener('resize', this.onResize)
    this.clearObjects()
    this.controls.dispose()
    this.renderer.dispose()
    this.domElement.remove()
  }

  private animate = (): void => {
    this.animationId = requestAnimationFrame(this.animate)
    const elapsed = this.clock.getElapsedTime()
    this.controls.update()
    if (this.viewOptions.visual.animations) {
      this.updateAnimatedBorders(elapsed)
      this.updateActivityPulse(elapsed)
      if (this.objects?.tileMaterial && 'terrainUniforms' in this.objects.tileMaterial) {
        updateTileMaterialTime(this.objects.tileMaterial, elapsed)
      }
    }
    this.renderer.render(this.scene, this.camera)
  }

  private applySceneMode(): void {
    const flatGround = layoutUsesFlatGround(this.viewOptions.layout.mode)
    this.ground.visible = flatGround
    this.controls.maxPolarAngle = flatGround ? Math.PI / 2.05 : Math.PI
    if (this.viewOptions.layout.mode === 'sphere') {
      this.scene.fog = new THREE.Fog(0x0b1220, 80, 420)
    } else {
      this.scene.fog = new THREE.Fog(0x0b1220, 40, 220)
    }
  }

  private onResize = (): void => {
    const parent = this.domElement.parentElement
    if (!parent) {
      return
    }
    const width = parent.clientWidth
    const height = parent.clientHeight
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
  }

  private onPointerMove = (event: PointerEvent): void => {
    const rect = this.domElement.getBoundingClientRect()
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
    const node = this.pickNode()
    const nextId = node?.id ?? null
    if (nextId !== this.hoveredId) {
      this.hoveredId = nextId
      this.domElement.style.cursor = node ? 'pointer' : 'default'
    }
    this.callbacks.onHover(node, event.clientX, event.clientY)
  }

  private onPointerDown = (): void => {
    const node = this.pickNode()
    this.callbacks.onSelect(node)
  }

  private pickNode(): RepositoryTerrainNode | null {
    if (!this.objects) {
      return null
    }
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hits = this.raycaster.intersectObject(this.objects.tiles, false)
    if (hits.length === 0 || hits[0].instanceId === undefined) {
      return null
    }
    const node = this.nodes[hits[0].instanceId]
    return node ?? null
  }

  private clearObjects(): void {
    if (!this.objects) {
      return
    }
    for (const mesh of [
      this.objects.tiles,
      this.objects.borders,
      this.objects.beacons,
      this.objects.agentMarkers,
    ]) {
      this.scene.remove(mesh)
      mesh.geometry.dispose()
      if (Array.isArray(mesh.material)) {
        mesh.material.forEach((material) => material.dispose())
      } else {
        mesh.material.dispose()
      }
    }
    for (const line of [this.objects.dependencyLines, this.objects.regionOutlines]) {
      this.scene.remove(line)
      line.geometry.dispose()
      if (Array.isArray(line.material)) {
        line.material.forEach((material) => material.dispose())
      } else {
        line.material.dispose()
      }
    }
    this.objects = null
  }

  private rebuildMeshes(
    nodes: RepositoryTerrainNode[],
    dependencies: TerrainDependency[],
  ): void {
    this.clearObjects()
    if (nodes.length === 0) {
      return
    }

    const sphereLayout = this.viewOptions.layout.mode === 'sphere'
    const solidStyle = this.viewOptions.visual.style === 'solid'
    const workingTreeEffects = !solidStyle && this.layers.workingTree
    const dummy = new THREE.Object3D()
    const tileGeometry = new THREE.BoxGeometry(1.8, 1, 1.8)
    setTileWorkingTreeAttributes(tileGeometry, nodes, workingTreeEffects)
    const tileMaterial = solidStyle
      ? createSimpleTileMaterial()
      : createTerrainTileMaterial()
    if (!solidStyle) {
      setTileWorkingTreeEnabled(tileMaterial as TerrainTileMaterial, workingTreeEffects)
    }
    const tiles = new THREE.InstancedMesh(tileGeometry, tileMaterial, nodes.length)
    tiles.instanceMatrix.setUsage(THREE.DynamicDrawUsage)

    const borderGeometry = new THREE.BoxGeometry(2.05, 0.08, 2.05)
    const borderMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.85 })
    const borders = new THREE.InstancedMesh(borderGeometry, borderMaterial, nodes.length)
    borders.instanceMatrix.setUsage(THREE.DynamicDrawUsage)

    const beaconGeometry = new THREE.CylinderGeometry(0.12, 0.18, 0.7, 8)
    const beaconMaterial = new THREE.MeshBasicMaterial()
    const beacons = new THREE.InstancedMesh(beaconGeometry, beaconMaterial, nodes.length)

    const agentGeometry = new THREE.OctahedronGeometry(0.35, 0)
    const agentMaterial = new THREE.MeshBasicMaterial({
      color: 0x67e8f9,
      transparent: true,
      opacity: solidStyle ? 1 : 0.75,
    })
    const agentMarkers = new THREE.InstancedMesh(agentGeometry, agentMaterial, nodes.length)

    nodes.forEach((node, index) => {
      const slot = this.layoutSlots[index] ?? {
        x: node.coordinates.x,
        y: 0,
        z: node.coordinates.y,
        normalX: 0,
        normalY: 1,
        normalZ: 0,
      }
      const height = tileHeight(node, this.layers, this.viewOptions.visual)
      placeTileOnSlot(dummy, slot, height, sphereLayout)
      tiles.setMatrixAt(index, dummy.matrix)
      tiles.setColorAt(index, tileColor(node, this.layers, this.viewOptions.visual))

      const borderKind = node.git.branch_kind
      const showBorder =
        this.layers.gitState &&
        borderKind !== 'default' &&
        borderKind !== 'other'
      if (showBorder) {
        const borderOffset = sphereLayout ? height + 0.12 : height + 0.06
        if (sphereLayout) {
          _normal.set(slot.normalX, slot.normalY, slot.normalZ)
          dummy.position.set(
            slot.x + _normal.x * borderOffset,
            slot.y + _normal.y * borderOffset,
            slot.z + _normal.z * borderOffset,
          )
          dummy.quaternion.setFromUnitVectors(_up, _normal)
        } else {
          dummy.position.set(slot.x, borderOffset, slot.z)
          dummy.quaternion.set(0, 0, 0, 1)
        }
        dummy.scale.set(1, 1, 1)
        dummy.updateMatrix()
        borders.setMatrixAt(index, dummy.matrix)
        const borderColor =
          BRANCH_BORDER_COLORS[borderKind] ?? BRANCH_BORDER_COLORS.other
        borders.setColorAt(index, borderColor)
      } else {
        dummy.position.set(0, -100, 0)
        dummy.scale.set(0, 0, 0)
        dummy.updateMatrix()
        borders.setMatrixAt(index, dummy.matrix)
      }

      if (this.layers.cicd && node.pipeline) {
        const beaconOffset = sphereLayout ? height + 0.65 : height + 0.55
        if (sphereLayout) {
          _normal.set(slot.normalX, slot.normalY, slot.normalZ)
          dummy.position.set(
            slot.x + _normal.x * beaconOffset,
            slot.y + _normal.y * beaconOffset,
            slot.z + _normal.z * beaconOffset,
          )
          dummy.quaternion.setFromUnitVectors(_up, _normal)
        } else {
          dummy.position.set(slot.x, beaconOffset, slot.z)
          dummy.quaternion.set(0, 0, 0, 1)
        }
        dummy.scale.set(1, 1, 1)
        dummy.updateMatrix()
        beacons.setMatrixAt(index, dummy.matrix)
        const beaconColor =
          PIPELINE_COLORS[node.pipeline.status] ?? PIPELINE_COLORS.unknown
        beacons.setColorAt(index, beaconColor)
      } else {
        dummy.position.set(0, -100, 0)
        dummy.scale.set(0, 0, 0)
        dummy.updateMatrix()
        beacons.setMatrixAt(index, dummy.matrix)
      }

      if (this.layers.agent && node.agent.documentation_score > 0.2) {
        const markerScale = node.agent.documentation_score
        const markerOffset = sphereLayout ? height + 1.25 : height + 1.1
        if (sphereLayout) {
          _normal.set(slot.normalX, slot.normalY, slot.normalZ)
          dummy.position.set(
            slot.x + _normal.x * markerOffset,
            slot.y + _normal.y * markerOffset,
            slot.z + _normal.z * markerOffset,
          )
          dummy.quaternion.setFromUnitVectors(_up, _normal)
        } else {
          dummy.position.set(slot.x, markerOffset, slot.z)
          dummy.quaternion.set(0, 0, 0, 1)
        }
        dummy.scale.set(markerScale, markerScale, markerScale)
        dummy.updateMatrix()
        agentMarkers.setMatrixAt(index, dummy.matrix)
      } else {
        dummy.position.set(0, -100, 0)
        dummy.scale.set(0, 0, 0)
        dummy.updateMatrix()
        agentMarkers.setMatrixAt(index, dummy.matrix)
      }
    })

    tiles.instanceMatrix.needsUpdate = true
    borders.instanceMatrix.needsUpdate = true
    beacons.instanceMatrix.needsUpdate = true
    agentMarkers.instanceMatrix.needsUpdate = true
    if (tiles.instanceColor) {
      tiles.instanceColor.needsUpdate = true
    }
    if (borders.instanceColor) {
      borders.instanceColor.needsUpdate = true
    }
    if (beacons.instanceColor) {
      beacons.instanceColor.needsUpdate = true
    }

    const dependencyLines = this.buildDependencyLines(nodes, dependencies)
    const regionOutlines =
      this.viewOptions.layout.mode === 'hierarchy'
        ? this.buildRegionOutlines(nodes)
        : this.buildEmptyLines()

    this.scene.add(tiles, borders, beacons, agentMarkers, dependencyLines, regionOutlines)
    this.objects = {
      tiles,
      tileMaterial,
      borders,
      beacons,
      dependencyLines,
      regionOutlines,
      agentMarkers,
    }
  }

  private buildDependencyLines(
    nodes: RepositoryTerrainNode[],
    dependencies: TerrainDependency[],
  ): THREE.LineSegments {
    const positions: number[] = []
    const colors: number[] = []
    const byId = new Map(nodes.map((node, index) => [node.id, index]))
    const sphereLayout = this.viewOptions.layout.mode === 'sphere'

    if (this.layers.dependencies) {
      for (const dep of dependencies) {
        const fromIndex = byId.get(dep.from_id)
        const toIndex = byId.get(dep.to_id)
        if (fromIndex === undefined || toIndex === undefined) {
          continue
        }
        const from = nodes[fromIndex]
        const to = nodes[toIndex]
        const fromSlot = this.layoutSlots[fromIndex]
        const toSlot = this.layoutSlots[toIndex]
        if (!from || !to || !fromSlot || !toSlot) {
          continue
        }
        const fromHeight = tileHeight(from, this.layers, this.viewOptions.visual) + 0.4
        const toHeight = tileHeight(to, this.layers, this.viewOptions.visual) + 0.4
        const fx = fromSlot.x
        const fy = fromSlot.y + (sphereLayout ? fromSlot.normalY * fromHeight : fromHeight)
        const fz = fromSlot.z
        const tx = toSlot.x
        const ty = toSlot.y + (sphereLayout ? toSlot.normalY * toHeight : toHeight)
        const tz = toSlot.z
        const midY = Math.max(fy, ty) + 4 + dep.consumer_count * 0.35
        positions.push(fx, fy, fz, fx, midY, fz)
        positions.push(fx, midY, fz, tx, midY, tz)
        positions.push(tx, midY, tz, tx, ty, tz)
        const color =
          dep.health === 'broken'
            ? new THREE.Color(0xef4444)
            : dep.health === 'outdated'
              ? new THREE.Color(0xeab308)
              : new THREE.Color(0x22c55e)
        for (let segment = 0; segment < 3; segment += 1) {
          colors.push(color.r, color.g, color.b, color.r, color.g, color.b)
        }
      }
    }

    return this.linesFromPositions(positions, colors)
  }

  private buildEmptyLines(): THREE.LineSegments {
    return this.linesFromPositions([0, -100, 0, 0, -100, 0], [], 0x334155, 0)
  }

  private linesFromPositions(
    positions: number[],
    colors: number[],
    solidColor?: number,
    opacity = 0.75,
  ): THREE.LineSegments {
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    if (colors.length > 0) {
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    }
    const material = solidColor
      ? new THREE.LineBasicMaterial({
          color: solidColor,
          transparent: opacity < 1,
          opacity,
        })
      : new THREE.LineBasicMaterial({
          vertexColors: true,
          transparent: true,
          opacity,
        })
    return new THREE.LineSegments(geometry, material)
  }

  private buildRegionOutlines(nodes: RepositoryTerrainNode[]): THREE.LineSegments {
    const positions: number[] = []
    const regionBuckets = new Map<string, RepositoryTerrainNode[]>()
    for (const node of nodes) {
      const key = `${node.project_name}::${node.coordinates.region ?? node.project_name}`
      const bucket = regionBuckets.get(key) ?? []
      bucket.push(node)
      regionBuckets.set(key, bucket)
    }
    for (const members of regionBuckets.values()) {
      const xs = members.map((node) => node.coordinates.x)
      const ys = members.map((node) => node.coordinates.y)
      const pad = 1.4
      const minX = Math.min(...xs) - pad
      const maxX = Math.max(...xs) + pad
      const minY = Math.min(...ys) - pad
      const maxY = Math.max(...ys) + pad
      const y = 0.05
      const corners: Array<[number, number, number]> = [
        [minX, y, minY],
        [maxX, y, minY],
        [maxX, y, maxY],
        [minX, y, maxY],
        [minX, y, minY],
      ]
      for (let index = 0; index < corners.length - 1; index += 1) {
        positions.push(...corners[index], ...corners[index + 1])
      }
    }
    return this.linesFromPositions(
      positions.length ? positions : [0, -100, 0, 0, -100, 0],
      [],
      0x334155,
      0.35,
    )
  }

  private updateAnimatedBorders(elapsed: number): void {
    if (!this.objects || !this.layers.gitState || !this.viewOptions.visual.animations) {
      return
    }
    const material = this.objects.borders.material
    if (!(material instanceof THREE.MeshBasicMaterial)) {
      return
    }
    const pulse = 0.45 + Math.sin(elapsed * 4) * 0.35
    for (const node of this.nodes) {
      if (node.git.branch_kind === 'detached') {
        material.opacity = pulse
        break
      }
    }
  }

  private updateActivityPulse(elapsed: number): void {
    if (
      !this.objects ||
      !this.layers.terrain ||
      !this.viewOptions.visual.animations ||
      this.viewOptions.visual.style === 'solid'
    ) {
      return
    }
    const sphereLayout = this.viewOptions.layout.mode === 'sphere'
    const dummy = new THREE.Object3D()
    let changed = false
    this.nodes.forEach((node, index) => {
      if (node.activity.pulse_intensity <= 0) {
        return
      }
      const slot = this.layoutSlots[index]
      if (!slot) {
        return
      }
      const baseHeight = tileHeight(node, this.layers, this.viewOptions.visual)
      const pulse = 1 + Math.sin(elapsed * 3 + index) * 0.04 * node.activity.pulse_intensity
      const height = baseHeight * pulse
      placeTileOnSlot(dummy, slot, height, sphereLayout)
      this.objects?.tiles.setMatrixAt(index, dummy.matrix)
      changed = true
    })
    if (changed && this.objects) {
      this.objects.tiles.instanceMatrix.needsUpdate = true
    }
  }

  private fitCamera(nodes: RepositoryTerrainNode[]): void {
    if (nodes.length === 0) {
      return
    }
    if (this.viewOptions.layout.mode === 'sphere') {
      const radius = Math.max(
        ...this.layoutSlots.map((slot) => Math.hypot(slot.x, slot.y, slot.z)),
        14,
      )
      this.controls.target.set(0, 0, 0)
      const distance = radius * 2.8
      this.camera.position.set(distance * 0.65, distance * 0.45, distance * 0.75)
      this.controls.update()
      return
    }

    const xs = this.layoutSlots.map((slot) => slot.x)
    const zs = this.layoutSlots.map((slot) => slot.z)
    const centerX = (Math.min(...xs) + Math.max(...xs)) / 2
    const centerZ = (Math.min(...zs) + Math.max(...zs)) / 2
    this.controls.target.set(centerX, 0, centerZ)
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...zs) - Math.min(...zs))
    const distance = Math.max(24, span * 1.4)
    this.camera.position.set(centerX + distance * 0.55, distance * 0.75, centerZ + distance * 0.65)
    this.controls.update()
  }
}
