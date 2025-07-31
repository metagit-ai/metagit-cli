import yaml
from typing import Optional
from metagit.core.detect.models import ProjectScanContext, DiscoveryResult


class DockerDetector:
    name = "DockerDetector"

    def should_run(self, ctx: ProjectScanContext) -> bool:
        return any(
            "dockerfile" in p.name.lower() or "docker-compose" in p.name.lower()
            for p in ctx.all_files
        )

    def run(self, ctx: ProjectScanContext) -> Optional[DiscoveryResult]:
        dockerfiles = [p for p in ctx.all_files if "dockerfile" in p.name.lower()]
        composefiles = [
            p
            for p in ctx.all_files
            if "docker-compose" in p.name.lower() and p.suffix in {".yml", ".yaml"}
        ]

        containers = []
        for dockerfile in dockerfiles:
            base_image = None
            exposed_ports = []
            entrypoint = None
            cmd = None

            try:
                with dockerfile.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.upper().startswith("FROM"):
                            base_image = line.split(None, 1)[1]
                        elif line.upper().startswith("EXPOSE"):
                            exposed_ports.extend(line.split()[1:])
                        elif line.upper().startswith("ENTRYPOINT"):
                            entrypoint = line[len("ENTRYPOINT") :].strip()
                        elif line.upper().startswith("CMD"):
                            cmd = line[len("CMD") :].strip()
            except Exception:
                continue  # corrupt file

            containers.append(
                {
                    "file": str(dockerfile.relative_to(ctx.root_path)),
                    "base_image": base_image,
                    "exposed_ports": exposed_ports,
                    "entrypoint": entrypoint,
                    "cmd": cmd,
                }
            )

        services = []
        for composefile in composefiles:
            try:
                with composefile.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        continue
                    for svc_name, svc_def in data.get("services", {}).items():
                        services.append(
                            {
                                "name": svc_name,
                                "image": svc_def.get("image"),
                                "build": svc_def.get("build"),
                                "ports": svc_def.get("ports", []),
                            }
                        )
            except Exception:
                continue

        if not containers and not services:
            return None

        return DiscoveryResult(
            name="Dockerized Project",
            description="Detected Dockerfile(s) or Compose configuration indicating containerization",
            tags=["docker", "container", "service"],
            confidence=0.95,
            data={
                "containers": containers,
                "compose_services": services,
            },
        )
