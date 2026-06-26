#!/usr/bin/env python
"""
Sampling-assisted bootstrap service for `.metagit.yml`.
"""

from typing import Callable, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.utils.yaml_class import yaml


class BootstrapSamplingService:
    """Generate `.metagit.yml` using sampling when available, otherwise fallback."""

    def __init__(
        self,
        sampling_supported: bool,
        sampler: Optional[Callable[[dict[str, str]], str]] = None,
    ) -> None:
        self.sampling_supported = sampling_supported
        self._sampler = sampler

    def generate(self, context: dict[str, str], confirm_write: bool = False) -> dict[str, str]:
        """Generate config draft and return write guidance."""
        if not self.sampling_supported or self._sampler is None:
            return {
                "mode": "plan_only",
                "prompt_package": self._build_prompt(context=context),
                "write_target": ".metagit.generated.yml",
            }

        errors: list[str] = []
        for _ in range(3):
            prompt = self._build_prompt(context=context, validation_errors=errors)
            draft_yaml = self._sampler({"prompt": prompt})
            validation = self._validate_yaml(draft_yaml=draft_yaml)
            if validation["valid"]:
                return {
                    "mode": "sampled",
                    "draft_yaml": draft_yaml,
                    "write_target": ".metagit.yml" if confirm_write else ".metagit.generated.yml",
                }
            errors = [validation["error"]]

        return {
            "mode": "plan_only",
            "prompt_package": self._build_prompt(context=context, validation_errors=errors),
            "write_target": ".metagit.generated.yml",
        }

    def _build_prompt(self, context: dict[str, str], validation_errors: Optional[list[str]] = None) -> str:
        errors = "\n".join(validation_errors or [])
        return (
            "Create a valid .metagit.yml using this context.\n"
            f"Context: {context}\n"
            f"Validation errors to fix: {errors if errors else 'none'}\n"
            "Output only YAML."
        )

    def _validate_yaml(self, draft_yaml: str) -> dict[str, str | bool]:
        try:
            loaded = yaml.safe_load(draft_yaml)
            MetagitConfig(**loaded)
            return {"valid": True, "error": ""}
        except Exception as exc:
            return {"valid": False, "error": str(exc)}
