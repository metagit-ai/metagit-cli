import * as THREE from 'three'

export interface TerrainTileMaterial extends THREE.MeshStandardMaterial {
  terrainUniforms: {
    uTime: { value: number }
    uWorkingTreeEnabled: { value: number }
  }
}

/** Flat MeshStandardMaterial without working-tree shader effects. */
export function createSimpleTileMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    roughness: 0.82,
    metalness: 0.02,
    flatShading: false,
  })
}

/** MeshStandardMaterial extended with working-tree surface shader injection. */
export function createTerrainTileMaterial(): TerrainTileMaterial {
  const material = new THREE.MeshStandardMaterial({
    roughness: 0.68,
    metalness: 0.1,
  }) as TerrainTileMaterial

  material.terrainUniforms = {
    uTime: { value: 0 },
    uWorkingTreeEnabled: { value: 1 },
  }

  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = material.terrainUniforms.uTime
    shader.uniforms.uWorkingTreeEnabled = material.terrainUniforms.uWorkingTreeEnabled

    shader.vertexShader = shader.vertexShader.replace(
      '#include <common>',
      `#include <common>
attribute float aFracture;
attribute float aFissure;
attribute float aCrack;
uniform float uTime;
uniform float uWorkingTreeEnabled;
varying float vFracture;
varying float vFissure;
varying float vCrack;
varying vec2 vSurfaceUv;`,
    )

    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
vFracture = aFracture * uWorkingTreeEnabled;
vFissure = aFissure * uWorkingTreeEnabled;
vCrack = aCrack * uWorkingTreeEnabled;
vSurfaceUv = vec2(position.x, position.z);
if (position.y > 0.35) {
  float seed = instanceMatrix[3][0] * 0.17 + instanceMatrix[3][2] * 0.23;
  float ridge = sin((position.x + seed) * 14.0) * cos((position.z - seed) * 13.0);
  float shard = abs(sin((position.x - position.z + seed) * 19.0));
  transformed.y += ridge * vFracture * 0.14;
  transformed.y -= shard * vFracture * 0.06;
  transformed.x += sin(uTime * 2.0 + seed + position.z * 8.0) * vCrack * 0.025;
  transformed.z += cos(uTime * 2.2 + seed + position.x * 8.0) * vCrack * 0.025;
}`,
    )

    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      `#include <common>
uniform float uTime;
uniform float uWorkingTreeEnabled;
varying float vFracture;
varying float vFissure;
varying float vCrack;
varying vec2 vSurfaceUv;`,
    )

    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
float crackMask = smoothstep(0.82, 0.98, abs(sin(vSurfaceUv.x * 22.0 + vSurfaceUv.y * 17.0)));
float fissureMask = smoothstep(0.7, 1.0, abs(cos(vSurfaceUv.x * 31.0 - vSurfaceUv.y * 27.0 + uTime * 1.5)));
float conflictPulse = 0.55 + 0.45 * sin(uTime * 7.0);
vec3 fractureTint = vec3(0.08, 0.1, 0.14) * vFracture * crackMask;
vec3 fissureGlow = vec3(0.15, 0.92, 1.0) * vFissure * fissureMask * (0.45 + 0.55 * sin(uTime * 4.0 + vSurfaceUv.x * 6.0));
vec3 conflictGlow = vec3(1.0, 0.12, 0.08) * vCrack * conflictPulse * (0.35 + crackMask * 0.65);
totalEmissiveRadiance += fractureTint + fissureGlow + conflictGlow;
diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * (1.0 - vFracture * 0.25), vFracture * crackMask);`,
    )
  }

  material.customProgramCacheKey = () => 'terrain-tile-working-tree-v1'
  return material
}

export function setTileWorkingTreeAttributes(
  geometry: THREE.BoxGeometry,
  nodes: Array<{
    visual: {
      surface_fracture: number
      fissure_glow: number
      crack_severity: number
    }
  }>,
  enabled: boolean,
): void {
  const count = nodes.length
  const fracture = new Float32Array(count)
  const fissure = new Float32Array(count)
  const crack = new Float32Array(count)
  for (let index = 0; index < count; index += 1) {
    const visual = nodes[index].visual
    fracture[index] = enabled ? visual.surface_fracture : 0
    fissure[index] = enabled ? visual.fissure_glow : 0
    crack[index] = enabled ? visual.crack_severity : 0
  }
  geometry.setAttribute('aFracture', new THREE.InstancedBufferAttribute(fracture, 1))
  geometry.setAttribute('aFissure', new THREE.InstancedBufferAttribute(fissure, 1))
  geometry.setAttribute('aCrack', new THREE.InstancedBufferAttribute(crack, 1))
}

export function updateTileMaterialTime(material: TerrainTileMaterial, elapsed: number): void {
  material.terrainUniforms.uTime.value = elapsed
}

export function setTileWorkingTreeEnabled(
  material: TerrainTileMaterial,
  enabled: boolean,
): void {
  material.terrainUniforms.uWorkingTreeEnabled.value = enabled ? 1 : 0
}
