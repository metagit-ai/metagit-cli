#!/usr/bin/env python
"""Azure DevOps Work Item Tracking client for campaign board linking."""

from __future__ import annotations

import base64
from typing import Any, Optional
from urllib.parse import quote

import requests

from metagit.core.workitem.models import ExternalWorkRef


class AzureDevOpsBoardClient:
    """Minimal WIT client. Tokens stay on the session, never in campaign YAML."""

    def __init__(
        self,
        *,
        api_token: str,
        organization: str,
        project: str,
        base_url: str = "https://dev.azure.com",
        session: Optional[requests.Session] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_token:
            raise ValueError("Azure DevOps API token is required")
        if not organization:
            raise ValueError("Azure DevOps organization is required")
        if not project:
            raise ValueError("Azure DevOps project is required")
        self._organization = organization
        self._project = project
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self.session = session or requests.Session()
        token = base64.b64encode(f":{api_token}".encode("utf-8")).decode("ascii")
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
            }
        )

    def create_item(
        self,
        *,
        title: str,
        description: str,
        kind: str,
        parent: Optional[ExternalWorkRef] = None,
    ) -> ExternalWorkRef | Exception:
        try:
            payload: list[dict[str, Any]] = [
                {"op": "add", "path": "/fields/System.Title", "value": title},
                {"op": "add", "path": "/fields/System.Description", "value": description},
            ]
            if parent is not None:
                parent_url = parent.url or self._work_item_api_url(parent.id)
                payload.append(
                    {
                        "op": "add",
                        "path": "/relations/-",
                        "value": {
                            "rel": "System.LinkTypes.Hierarchy-Reverse",
                            "url": parent_url,
                        },
                    }
                )
            work_item_type = quote(kind, safe="")
            endpoint = (
                f"{self._base_url}/{self._organization}/{quote(self._project, safe='')}"
                f"/_apis/wit/workitems/${work_item_type}"
            )
            response = self.session.post(
                endpoint,
                params={"api-version": "7.1"},
                json=payload,
                headers={"Content-Type": "application/json-patch+json"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            identifier = str(data.get("id") or "")
            if not identifier:
                return Exception("Azure DevOps work item create returned no id")
            web_url = None
            links = data.get("_links") if isinstance(data.get("_links"), dict) else {}
            html = links.get("html") if isinstance(links, dict) else None
            if isinstance(html, dict):
                web_url = html.get("href")
            if not web_url:
                web_url = (
                    f"{self._base_url}/{self._organization}/{self._project}"
                    f"/_workitems/edit/{identifier}"
                )
            return ExternalWorkRef(
                provider="azure_devops",
                id=identifier,
                url=web_url,
                organization=self._organization,
                project=self._project,
                kind=kind,
            )
        except Exception as exc:
            return exc

    def get_item(self, ref: ExternalWorkRef) -> ExternalWorkRef | Exception:
        try:
            endpoint = (
                f"{self._base_url}/{self._organization}/{quote(self._project, safe='')}"
                f"/_apis/wit/workitems/{quote(ref.id, safe='')}"
            )
            response = self.session.get(
                endpoint,
                params={"api-version": "7.1"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            identifier = str(data.get("id") or ref.id)
            fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
            kind = fields.get("System.WorkItemType") if isinstance(fields, dict) else ref.kind
            web_url = (
                f"{self._base_url}/{self._organization}/{self._project}"
                f"/_workitems/edit/{identifier}"
            )
            return ExternalWorkRef(
                provider="azure_devops",
                id=identifier,
                url=web_url,
                organization=self._organization,
                project=self._project,
                kind=str(kind) if kind else ref.kind,
            )
        except Exception as exc:
            return exc

    def _work_item_api_url(self, work_item_id: str) -> str:
        return (
            f"{self._base_url}/{self._organization}/{quote(self._project, safe='')}"
            f"/_apis/wit/workitems/{quote(work_item_id, safe='')}"
        )


__all__ = ["AzureDevOpsBoardClient"]
