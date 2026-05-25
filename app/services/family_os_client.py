"""
HTTP client for the family-os REST API.

The Assistant is a separate service and a separate database. To create
events or grocery items in family-os we POST through its REST API rather
than reaching into its database directly. This keeps family-os as the
single source of truth and respects its validation layer.

Auth: a shared bearer token (`FAMILY_OS_SERVICE_TOKEN`) configured on both
sides. family-os's internal-routes middleware accepts any request that
presents a matching token. There's no per-user identity on these calls —
the family_id is the only authorization scope.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class FamilyOsClient:
    """Thin async wrapper over httpx — one method per family-os operation we need."""

    def __init__(self) -> None:
        s = get_settings()
        self._base = s.family_os_api_url.rstrip("/")
        self._token = s.family_os_service_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def create_family_event(
        self,
        family_id: str,
        *,
        title: str,
        start_minutes: int,
        end_minutes: int,
        is_recurring: bool = False,
        days_of_week: list[int] | None = None,
        date: str | None = None,
        assignee_type: str = "family",
        location: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a one-time or recurring family event.

        For one-time events: pass `date="YYYY-MM-DD"`, leave `days_of_week`
        empty, `is_recurring=False`.
        For recurring: pass `days_of_week` as 0-6 (Sun=0), `is_recurring=True`.
        """
        body = {
            "title": title,
            "startMinutes": start_minutes,
            "endMinutes": end_minutes,
            "isRecurring": is_recurring,
            "daysOfWeek": days_of_week or [],
            "assigneeType": assignee_type,
        }
        if date is not None:
            body["date"] = date
        if location is not None:
            body["location"] = location

        url = f"{self._base}/v1/internal/family/{family_id}/family-events"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, headers=self._headers(), json=body)
            r.raise_for_status()
            return r.json()

    async def create_note(
        self,
        family_id: str,
        *,
        body: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Add a note. Always created unpinned; user pins manually in the app."""
        payload: dict[str, Any] = {"body": body}
        if title is not None:
            payload["title"] = title

        url = f"{self._base}/v1/internal/family/{family_id}/notes"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()

    async def create_chore(
        self,
        family_id: str,
        *,
        title: str,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a chore. `assigned_to` is free-text Hebrew (e.g. "עודד"); the
        server tries to resolve it to a known familyMember.displayName and
        link `assignedToMemberId`, falling back to free-text on no match.
        """
        body: dict[str, Any] = {"title": title}
        if assigned_to is not None:
            body["assignedTo"] = assigned_to

        url = f"{self._base}/v1/internal/family/{family_id}/chores"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, headers=self._headers(), json=body)
            r.raise_for_status()
            return r.json()

    async def create_grocery_item(
        self,
        family_id: str,
        *,
        title: str,
        qty: str | None = None,
        shopping_category: str = "grocery",
        subcategory: str | None = None,
    ) -> dict[str, Any]:
        """Add an item to the family's shopping list."""
        body: dict[str, Any] = {
            "title": title,
            "shoppingCategory": shopping_category,
        }
        if qty is not None:
            body["qty"] = qty
        if subcategory is not None:
            body["subcategory"] = subcategory

        url = f"{self._base}/v1/internal/family/{family_id}/grocery"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, headers=self._headers(), json=body)
            r.raise_for_status()
            return r.json()


    # ── reads ─────────────────────────────────────────────────────────────

    async def list_family_events(
        self,
        family_id: str,
        *,
        range_: str = "today",
    ) -> list[dict[str, Any]]:
        """`range_` is one of: 'today' / 'tomorrow' / 'week'."""
        url = f"{self._base}/v1/internal/family/{family_id}/family-events"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                url, headers=self._headers(), params={"range": range_}
            )
            r.raise_for_status()
            return r.json()

    async def list_grocery(
        self,
        family_id: str,
        *,
        status: str = "unchecked",
    ) -> list[dict[str, Any]]:
        """`status` is one of: 'unchecked' (default) / 'all'."""
        url = f"{self._base}/v1/internal/family/{family_id}/grocery"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                url, headers=self._headers(), params={"status": status}
            )
            r.raise_for_status()
            return r.json()

    async def list_chores(
        self,
        family_id: str,
        *,
        status: str = "undone",
    ) -> list[dict[str, Any]]:
        """`status` is one of: 'undone' (default) / 'all'."""
        url = f"{self._base}/v1/internal/family/{family_id}/chores"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                url, headers=self._headers(), params={"status": status}
            )
            r.raise_for_status()
            return r.json()


family_os_client = FamilyOsClient()
