#!/usr/bin/env python
"""Campaign ↔ EverRoom Room association lifecycle (attach, create, detach, sync)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from metagit.core.campaign.context import CampaignContextService, generated_document_id, generated_document_markdown
from metagit.core.campaign.context_models import CampaignContextResult, ContextSummary, ProviderHealth
from metagit.core.campaign.everroom_provider import EverRoomCampaignContextProvider
from metagit.core.campaign.models import CampaignContextProviderConfig, CampaignDocument
from metagit.core.campaign.service import CampaignService
from metagit.core.integrations.everroom.client import EverRoomHttpClient
from metagit.core.integrations.everroom.errors import EverRoomError


class EverRoomSettings(BaseModel):
    """Resolved EverRoom connection settings. Token is never persisted to YAML."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str = "http://127.0.0.1:3210"
    token: str = ""
    timeout_seconds: float = 8.0


class EverRoomAttachResult(BaseModel):
    """Outcome of associating a campaign with an existing Room."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    room_id: str
    room_title: Optional[str] = None
    endpoint: str
    status: str = "AVAILABLE"


class EverRoomSyncResult(BaseModel):
    """Outcome of projecting MetaGit campaign state into a generated Room document."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    room_id: str
    document_id: str
    title: str
    version: int = 0
    generated: bool = True


class CampaignEverRoomService:
    """Mutating EverRoom operations. Detach never deletes a remote Room."""

    def __init__(
        self,
        *,
        campaign_service: CampaignService,
        context_service: CampaignContextService,
        settings: EverRoomSettings,
        client: Optional[EverRoomHttpClient] = None,
    ) -> None:
        self._campaigns = campaign_service
        self._context = context_service
        self._settings = settings
        self._client = client

    def status(self, slug: str) -> ProviderHealth:
        campaign = self._require_campaign(slug)
        provider = campaign.everroom_provider()
        if provider is None:
            return ProviderHealth(
                provider_type="everroom",
                status="NOT_CONFIGURED",
                message="No EverRoom Room is associated with this campaign.",
                endpoint=self._settings.endpoint,
            )
        client = self._client_for(provider)
        adapter = EverRoomCampaignContextProvider(campaign=campaign, config=provider, client=client)
        return adapter.health()

    def summarize(self, slug: str) -> ContextSummary:
        campaign = self._require_campaign(slug)
        provider = campaign.everroom_provider()
        if provider is None:
            return ContextSummary(
                provider_type="everroom",
                status="NOT_CONFIGURED",
                message="No EverRoom Room is associated with this campaign.",
            )
        client = self._client_for(provider)
        adapter = EverRoomCampaignContextProvider(campaign=campaign, config=provider, client=client)
        return adapter.summarize()

    def attach(self, slug: str, *, room_id: str, endpoint: Optional[str] = None) -> EverRoomAttachResult:
        campaign = self._require_campaign(slug)
        resolved_endpoint = (endpoint or self._settings.endpoint).rstrip("/")
        client = self._client or EverRoomHttpClient(
            endpoint=resolved_endpoint,
            token=self._settings.token,
            timeout_seconds=self._settings.timeout_seconds,
        )
        try:
            client.health()
            room = client.resolve_room(room_id)
        except EverRoomError:
            raise
        self._campaigns.upsert_context_provider(
            slug,
            CampaignContextProviderConfig(type="everroom", room_id=room.id, endpoint=resolved_endpoint),
        )
        verified = client.resolve_room(room.id)
        return EverRoomAttachResult(
            slug=campaign.slug,
            room_id=verified.id,
            room_title=verified.title or room.title,
            endpoint=resolved_endpoint,
            status="AVAILABLE",
        )

    def create_room(self, slug: str, *, endpoint: Optional[str] = None) -> EverRoomAttachResult:
        campaign = self._require_campaign(slug)
        resolved_endpoint = (endpoint or self._settings.endpoint).rstrip("/")
        client = self._client or EverRoomHttpClient(
            endpoint=resolved_endpoint,
            token=self._settings.token,
            timeout_seconds=self._settings.timeout_seconds,
        )
        client.health()
        created = client.create_room(
            title=campaign.title[:120],
            description=_room_description(campaign),
        )
        return self.attach(slug, room_id=created.room.id, endpoint=resolved_endpoint)

    def detach(self, slug: str) -> CampaignDocument:
        """Remove the association only. The EverRoom Room is left intact."""
        return self._campaigns.remove_context_provider(slug, "everroom")

    def sync(self, slug: str) -> EverRoomSyncResult:
        campaign = self._require_campaign(slug)
        provider = campaign.everroom_provider()
        if provider is None or not provider.room_id:
            raise EverRoomError("Attach an EverRoom Room before syncing campaign context.", status="NOT_CONFIGURED")
        client = self._client_for(provider)
        try:
            client.health()
            client.resolve_room(provider.room_id)
        except EverRoomError:
            raise
        packet = self._context.resolve(slug)
        document_id = generated_document_id(slug)
        markdown = generated_document_markdown(packet)
        document = client.upsert_generated_document(
            room_id=provider.room_id,
            document_id=document_id,
            title="Campaign Context (generated by MetaGit)",
            markdown=markdown,
        )
        return EverRoomSyncResult(
            slug=slug,
            room_id=provider.room_id,
            document_id=document.id,
            title=document.title,
            version=document.version,
            generated=True,
        )

    def context(self, slug: str, *, include: Optional[list[str]] = None) -> CampaignContextResult:
        return self._context.resolve(slug, include=include)

    def _require_campaign(self, slug: str) -> CampaignDocument:
        campaign = self._campaigns.load(slug)
        if campaign is None:
            raise ValueError(f"Unknown campaign: {slug!r}")
        return campaign

    def _client_for(self, provider: CampaignContextProviderConfig) -> EverRoomHttpClient:
        if self._client is not None:
            return self._client
        return EverRoomHttpClient(
            endpoint=provider.endpoint or self._settings.endpoint,
            token=self._settings.token,
            timeout_seconds=self._settings.timeout_seconds,
        )


def _room_description(campaign: CampaignDocument) -> str:
    repos = ", ".join(f"{entry.project}/{entry.repo}" for entry in campaign.repos[:40]) or "none"
    objective = campaign.goal or "No objective recorded."
    return (
        f"Derived Context Room for MetaGit campaign `{campaign.slug}`.\n"
        f"Status: {campaign.status}.\n"
        f"Objective: {objective}\n"
        f"Participating repositories: {repos}\n"
        "This Room profile is a projection of campaign metadata. "
        "MetaGit remains authoritative for campaign identity, topology, and Git state."
    )[:2000]


class EverRoomStatusView(BaseModel):
    """Human/JSON status combining MetaGit campaign and EverRoom health."""

    model_config = ConfigDict(extra="forbid")

    campaign: str
    campaign_status: str
    objective: Optional[str] = None
    metagit: dict[str, int] = Field(default_factory=dict)
    everroom: ProviderHealth
