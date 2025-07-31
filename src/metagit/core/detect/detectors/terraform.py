import hcl2
from pathlib import Path
from typing import Optional
from metagit.core.detect.models import ProjectScanContext, DiscoveryResult

def classify_module_source(source: str) -> str:
    source = source.strip()
    if source.startswith(("./", "../")) or not any(source.startswith(p) for p in ("git::", "http", "s3::", "gcs::", "terraform-")):
        return "local"
    return "remote"

class TerraformDetector:
    name = "TerraformDetector"

    def should_run(self, ctx: ProjectScanContext) -> bool:
        return any(p.suffix == '.tf' for p in ctx.all_files)

    def run(self, ctx: ProjectScanContext) -> Optional[DiscoveryResult]:
        provider_set = set()
        module_sources = []
        backend_type = None

        for tf_file in [p for p in ctx.all_files if p.suffix == ".tf"]:
            with tf_file.open("r", encoding="utf-8") as f:
                try:
                    parsed = hcl2.load(f)
                except Exception:
                    continue

                # Providers
                for block in parsed.get("provider", []):
                    for provider_name in block:
                        provider_set.add(provider_name)

                # Modules
                for block in parsed.get("module", []):
                    for module_name, attrs in block.items():
                        source = attrs.get("source")
                        if source:
                            module_sources.append({
                                "name": module_name,
                                "source": source,
                                "type": classify_module_source(source)
                            })

                # Terraform block (for backend)
                for block in parsed.get("terraform", []):
                    backend = block.get("backend")
                    if backend and isinstance(backend, dict):
                        backend_type = next(iter(backend.keys()), None)

        if not provider_set and not module_sources:
            return None

        return DiscoveryResult(
            name="Terraform Root Module",
            description="Detected a Terraform root module",
            tags=["terraform", "iac", "root-module"],
            confidence=0.95,
            data={
                "providers": sorted(provider_set),
                "modules": module_sources,
                "backend": backend_type,
            }
        )