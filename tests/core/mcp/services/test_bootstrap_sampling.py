#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.bootstrap_sampling
"""

from metagit.core.mcp.services.bootstrap_sampling import BootstrapSamplingService


def test_sampling_disabled_returns_plan_only_payload() -> None:
    service = BootstrapSamplingService(sampling_supported=False)

    result = service.generate(context={"repo_root": "/tmp/repo"}, confirm_write=False)

    assert result["mode"] == "plan_only"
    assert "prompt_package" in result
    assert result["write_target"] == ".metagit.generated.yml"


def test_sampling_success_returns_draft_yaml() -> None:
    def sampler(payload: dict[str, str]) -> str:
        _ = payload
        return "\n".join(
            [
                "name: generated",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        ) + "\n"

    service = BootstrapSamplingService(sampling_supported=True, sampler=sampler)

    result = service.generate(context={"repo_root": "/tmp/repo"}, confirm_write=True)

    assert result["mode"] == "sampled"
    assert "draft_yaml" in result
    assert result["write_target"] == ".metagit.yml"
