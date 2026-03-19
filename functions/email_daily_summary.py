"""
Gmail email fetch tool (last N hours) using WowBits Connectors.

This tool intentionally does NOT read environment variables. OAuth credentials are
read from a connector's config stored in the DB.
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from pylibs.connector import ConnectorManager


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DEFAULT_CONNECTOR_NAME = "gmail"


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        # allow comma-separated string
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    return [str(value)]


def _get_header(headers: List[Dict[str, str]], name: str) -> Optional[str]:
    name_l = name.lower()
    for h in headers or []:
        if str(h.get("name", "")).lower() == name_l:
            v = h.get("value")
            return str(v) if v is not None else None
    return None


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    # Gmail uses base64url without padding
    rem = len(data) % 4
    if rem:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _extract_text_plain(payload: Dict[str, Any]) -> str:
    """
    Try to extract a human-readable plain text body from Gmail message payload.
    Best-effort: prefers text/plain parts; falls back to top-level body data.
    """
    if not payload:
        return ""

    mime_type = payload.get("mimeType")
    body = payload.get("body") or {}
    data = body.get("data")
    if isinstance(data, str) and data:
        return _decode_b64url(data)

    parts = payload.get("parts") or []
    if not isinstance(parts, list):
        return ""

    # Prefer text/plain
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("mimeType") == "text/plain":
            pdata = (part.get("body") or {}).get("data")
            if isinstance(pdata, str) and pdata:
                return _decode_b64url(pdata)

    # Recurse into multipart/*
    if mime_type and str(mime_type).startswith("multipart/"):
        for part in parts:
            if isinstance(part, dict):
                txt = _extract_text_plain(part)
                if txt.strip():
                    return txt

    return ""


@dataclass
class _GmailConnectorConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    scopes: List[str]


def _load_gmail_config(connector_name: str) -> _GmailConnectorConfig:
    cm = ConnectorManager()
    connector = cm.get_connector(connector_name)
    if not connector:
        raise ValueError(
            f"Connector '{connector_name}' not found. Create a connector with provider 'gmail' and config "
            f"including client_id, client_secret, refresh_token."
        )
    config = connector.get("config") or {}
    # Allow a few common key variants (useful for 'custom' connectors)
    client_id = (config.get("client_id") or config.get("clientId") or "").strip()
    client_secret = (config.get("client_secret") or config.get("clientSecret") or "").strip()
    refresh_token = (config.get("refresh_token") or config.get("refreshToken") or "").strip()
    scopes = _as_list(config.get("scopes")) or [GMAIL_READONLY_SCOPE]

    # If user only provided an API key, explain why it won't work for mailbox reads.
    api_key = (
        (config.get("gmail-api") or config.get("gmail_api") or config.get("gmail_api_key") or config.get("api_key"))
        if isinstance(config, dict)
        else None
    )
    if api_key and not (client_id and client_secret and refresh_token):
        raise ValueError(
            "Gmail inbox access cannot use an API key alone. "
            "To read emails you must use OAuth user consent (recommended) and store these in the connector config: "
            "client_id, client_secret, refresh_token. "
            "Alternatively, for Google Workspace you can use a service account with Domain-Wide Delegation."
        )

    missing = [k for k, v in (("client_id", client_id), ("client_secret", client_secret), ("refresh_token", refresh_token)) if not v]
    if missing:
        raise ValueError(
            f"Connector '{connector_name}' is missing required fields: {', '.join(missing)}. "
            "Update the connector config."
        )

    return _GmailConnectorConfig(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        scopes=scopes,
    )


def _build_gmail_service(cfg: _GmailConnectorConfig):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError(
            "Missing Google dependencies. Ensure functions/requirements.txt includes "
            "'google-api-python-client' and 'google-auth'."
        ) from e

    creds = Credentials(
        token=None,
        refresh_token=cfg.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        scopes=cfg.scopes,
    )

    # Ensure we have an access token (refresh_token flow)
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _fetch_emails_sync(
    connector_name: str,
    max_results: int,
    label_ids: Optional[List[str]],
    include_body: bool,
    query: Optional[str],
    after_unix: Optional[int],
    before_unix: Optional[int],
    include_label_counts: bool,
) -> Dict[str, Any]:
    cfg = _load_gmail_config(connector_name)
    service = _build_gmail_service(cfg)

    q_parts: List[str] = []
    if query and str(query).strip():
        q_parts.append(str(query).strip())
    if after_unix is not None:
        q_parts.append(f"after:{int(after_unix)}")
    if before_unix is not None:
        q_parts.append(f"before:{int(before_unix)}")
    q = " ".join(q_parts).strip() or None

    # messages.list
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=q, labelIds=label_ids or None, maxResults=max_results)
        .execute()
    )
    msgs = resp.get("messages") or []

    label_counts: Optional[Dict[str, Any]] = None
    if include_label_counts:
        label_counts = {}
        # If label_ids not specified, default to INBOX since that is usually what people mean.
        labels_to_fetch = label_ids or ["INBOX"]
        for lid in labels_to_fetch:
            try:
                linfo = service.users().labels().get(userId="me", id=lid).execute()
                label_counts[lid] = {
                    "messagesTotal": linfo.get("messagesTotal"),
                    "messagesUnread": linfo.get("messagesUnread"),
                    "threadsTotal": linfo.get("threadsTotal"),
                    "threadsUnread": linfo.get("threadsUnread"),
                }
            except Exception:
                # Best-effort; keep going if a label doesn't exist.
                continue

    emails: List[Dict[str, Any]] = []
    for m in msgs:
        mid = m.get("id")
        if not mid:
            continue

        fmt = "full" if include_body else "metadata"
        md = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=mid,
                format=fmt,
                metadataHeaders=["From", "To", "Cc", "Bcc", "Subject", "Date", "Reply-To"],
            )
            .execute()
        )

        payload = md.get("payload") or {}
        headers = payload.get("headers") or []
        internal_date = md.get("internalDate")
        date_hdr = _get_header(headers, "Date")
        parsed_date_iso = None
        if isinstance(date_hdr, str) and date_hdr.strip():
            try:
                parsed_date_iso = parsedate_to_datetime(date_hdr).isoformat()
            except Exception:
                parsed_date_iso = None

        item: Dict[str, Any] = {
            "id": md.get("id"),
            "threadId": md.get("threadId"),
            "labels": md.get("labelIds") or [],
            "internalDate": int(internal_date) if internal_date is not None else None,  # ms epoch
            "date": parsed_date_iso,
            "from": _get_header(headers, "From"),
            "to": _get_header(headers, "To"),
            "subject": _get_header(headers, "Subject"),
            "snippet": md.get("snippet") or "",
        }

        if include_body:
            item["body_text"] = _extract_text_plain(payload)

        emails.append(item)

    return {
        "status": "success",
        "connector_name": connector_name,
        "query": q,
        "filters": {"label_ids": label_ids or None, "after_unix": after_unix, "before_unix": before_unix},
        "count": len(emails),
        "emails": emails,
        "label_counts": label_counts,
    }


async def email_daily_summary(
    connector_name: Optional[str] = None,
    max_results: int = 50,
    label_ids: Optional[List[str]] = None,
    include_body: bool = False,
    query: Optional[str] = None,
    after_unix: Optional[int] = None,
    before_unix: Optional[int] = None,
    include_label_counts: bool = False,
) -> Dict[str, Any]:
    """
    Fetch emails from Gmail using Gmail search query and/or time bounds.

    Credentials are read from the connector config (DB). Required connector fields:
    - client_id
    - client_secret
    - refresh_token
    Optional:
    - scopes (list or comma-separated string; default gmail.readonly)

    Filters (any combination):
    - query: Gmail search query (e.g. 'in:inbox newer_than:7d', 'from:amazon subject:invoice')
    - after_unix: include messages after this unix timestamp (seconds)
    - before_unix: include messages before this unix timestamp (seconds)
    - include_label_counts: when true, also returns totals for requested label_ids (default INBOX)
    """
    try:
        resolved_connector = (connector_name or DEFAULT_CONNECTOR_NAME).strip()
        if not resolved_connector:
            return {
                "status": "error",
                "error": "connector_name is required (or set DEFAULT_CONNECTOR_NAME at top of tool)",
            }
        if max_results <= 0 or max_results > 500:
            return {"status": "error", "error": "max_results must be between 1 and 500"}
        if label_ids is not None and not isinstance(label_ids, list):
            return {"status": "error", "error": "label_ids must be a list of strings or null"}
        if after_unix is not None and int(after_unix) < 0:
            return {"status": "error", "error": "after_unix must be a unix timestamp (seconds) >= 0"}
        if before_unix is not None and int(before_unix) < 0:
            return {"status": "error", "error": "before_unix must be a unix timestamp (seconds) >= 0"}
        if after_unix is not None and before_unix is not None and int(after_unix) >= int(before_unix):
            return {"status": "error", "error": "after_unix must be < before_unix"}

        return await asyncio.to_thread(
            _fetch_emails_sync,
            connector_name=resolved_connector,
            max_results=int(max_results),
            label_ids=[str(x) for x in (label_ids or [])] or None,
            include_body=bool(include_body),
            query=query,
            after_unix=int(after_unix) if after_unix is not None else None,
            before_unix=int(before_unix) if before_unix is not None else None,
            include_label_counts=bool(include_label_counts),
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}

