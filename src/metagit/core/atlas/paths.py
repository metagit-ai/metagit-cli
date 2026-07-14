#!/usr/bin/env python
"""Resolve Atlas persistence paths under a repository root."""

from __future__ import annotations

from pathlib import Path

ATLAS_DIRNAME = ".atlas"


def _repo_root(repo_root: str | Path) -> Path:
  return Path(repo_root)


def atlas_root(repo_root: str | Path) -> Path:
  """Return ``.atlas`` under the repository root."""
  return _repo_root(repo_root) / ATLAS_DIRNAME


def atlas_yaml_path(repo_root: str | Path) -> Path:
  """Return the Atlas configuration file path."""
  return atlas_root(repo_root) / "atlas.yaml"


def ontology_dir(repo_root: str | Path) -> Path:
  """Return the curated ontology directory."""
  return atlas_root(repo_root) / "ontology"


def domain_file(repo_root: str | Path) -> Path:
  """Return the domain vocabulary file path."""
  return ontology_dir(repo_root) / "domain.yaml"


def concepts_file(repo_root: str | Path) -> Path:
  """Return the concepts catalog file path."""
  return ontology_dir(repo_root) / "concepts.yaml"


def capabilities_file(repo_root: str | Path) -> Path:
  """Return the capabilities catalog file path."""
  return ontology_dir(repo_root) / "capabilities.yaml"


def extensions_dir(repo_root: str | Path) -> Path:
  """Return the ontology extensions directory."""
  return ontology_dir(repo_root) / "extensions"


def intent_dir(repo_root: str | Path) -> Path:
  """Return the curated intent directory."""
  return atlas_root(repo_root) / "intent"


def contracts_dir(repo_root: str | Path) -> Path:
  """Return the contracts directory."""
  return intent_dir(repo_root) / "contracts"


def invariants_dir(repo_root: str | Path) -> Path:
  """Return the invariants directory."""
  return intent_dir(repo_root) / "invariants"


def decisions_dir(repo_root: str | Path) -> Path:
  """Return the decisions directory."""
  return intent_dir(repo_root) / "decisions"


def risks_dir(repo_root: str | Path) -> Path:
  """Return the risks directory."""
  return intent_dir(repo_root) / "risks"


def ownership_dir(repo_root: str | Path) -> Path:
  """Return the ownership directory."""
  return intent_dir(repo_root) / "ownership"


def generated_dir(repo_root: str | Path) -> Path:
  """Return the generated evidence directory."""
  return atlas_root(repo_root) / "generated"


def inventory_file(repo_root: str | Path) -> Path:
  """Return the file inventory path."""
  return generated_dir(repo_root) / "inventory.yaml"


def symbols_file(repo_root: str | Path) -> Path:
  """Return the symbol catalog path."""
  return generated_dir(repo_root) / "symbols.yaml"


def interfaces_file(repo_root: str | Path) -> Path:
  """Return the interface catalog path."""
  return generated_dir(repo_root) / "interfaces.yaml"


def dependencies_file(repo_root: str | Path) -> Path:
  """Return the dependency graph path."""
  return generated_dir(repo_root) / "dependencies.yaml"


def verifications_file(repo_root: str | Path) -> Path:
  """Return the verification evidence path."""
  return generated_dir(repo_root) / "verifications.yaml"


def generated_imports_dir(repo_root: str | Path) -> Path:
  """Return the generated adapter imports directory."""
  return generated_dir(repo_root) / "imports"


def manifests_dir(repo_root: str | Path) -> Path:
  """Return the generated manifests directory."""
  return generated_dir(repo_root) / "manifests"


def mappings_dir(repo_root: str | Path) -> Path:
  """Return the semantic-to-evidence mappings directory."""
  return atlas_root(repo_root) / "mappings"


def semantic_to_evidence_file(repo_root: str | Path) -> Path:
  """Return the semantic-to-evidence mapping file path."""
  return mappings_dir(repo_root) / "semantic-to-evidence.yaml"


def external_ids_file(repo_root: str | Path) -> Path:
  """Return the external identifier mapping file path."""
  return mappings_dir(repo_root) / "external-ids.yaml"


def overrides_dir(repo_root: str | Path) -> Path:
  """Return the curated overrides directory."""
  return atlas_root(repo_root) / "overrides"


def classifications_file(repo_root: str | Path) -> Path:
  """Return the classification overrides file path."""
  return overrides_dir(repo_root) / "classifications.yaml"


def links_file(repo_root: str | Path) -> Path:
  """Return the link overrides file path."""
  return overrides_dir(repo_root) / "links.yaml"


def suppressions_file(repo_root: str | Path) -> Path:
  """Return the suppression overrides file path."""
  return overrides_dir(repo_root) / "suppressions.yaml"


def federation_dir(repo_root: str | Path) -> Path:
  """Return the federation export/import directory."""
  return atlas_root(repo_root) / "federation"


def federation_export_file(repo_root: str | Path) -> Path:
  """Return the federation export configuration file path."""
  return federation_dir(repo_root) / "export.yaml"


def federation_imports_dir(repo_root: str | Path) -> Path:
  """Return the federation imports directory."""
  return federation_dir(repo_root) / "imports"


def policy_dir(repo_root: str | Path) -> Path:
  """Return the policy directory."""
  return atlas_root(repo_root) / "policy"


def access_file(repo_root: str | Path) -> Path:
  """Return the access policy file path."""
  return policy_dir(repo_root) / "access.yaml"


def generation_file(repo_root: str | Path) -> Path:
  """Return the generation policy file path."""
  return policy_dir(repo_root) / "generation.yaml"


def index_dir(repo_root: str | Path) -> Path:
  """Return the derived index directory."""
  return atlas_root(repo_root) / "index"


def index_entities_file(repo_root: str | Path) -> Path:
  """Return the derived entity index file path."""
  return index_dir(repo_root) / "entities.json"


__all__ = [
  "ATLAS_DIRNAME",
  "access_file",
  "atlas_root",
  "atlas_yaml_path",
  "capabilities_file",
  "classifications_file",
  "concepts_file",
  "contracts_dir",
  "decisions_dir",
  "dependencies_file",
  "domain_file",
  "extensions_dir",
  "external_ids_file",
  "federation_dir",
  "federation_export_file",
  "federation_imports_dir",
  "generated_dir",
  "generated_imports_dir",
  "generation_file",
  "index_dir",
  "index_entities_file",
  "intent_dir",
  "interfaces_file",
  "inventory_file",
  "invariants_dir",
  "links_file",
  "manifests_dir",
  "mappings_dir",
  "ontology_dir",
  "ownership_dir",
  "overrides_dir",
  "policy_dir",
  "risks_dir",
  "semantic_to_evidence_file",
  "suppressions_file",
  "symbols_file",
  "verifications_file",
]
