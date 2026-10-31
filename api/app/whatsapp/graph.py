"""Minimal WhatsApp Cloud API (Graph API) client: send a text, download a media file.

Phone numbers are passed through to Meta but never logged.
"""

import logging

import httpx

from app.config import Settings

log = logging.getLogger("billsaathi.whatsapp.graph")

MAX_BODY_CHARS = 4096  # WhatsApp text limit


class GraphError(Exception):
    pass


class GraphClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
            raise GraphError("WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required")
        self._phone_number_id = settings.whatsapp_phone_number_id
        self._base = (
            f"{settings.whatsapp_graph_base_url.rstrip('/')}/{settings.whatsapp_graph_version}"
        )
        self._http = httpx.Client(
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token.get_secret_value()}"
            },
            timeout=20.0,
            transport=transport,
        )

    def send_text(self, to: str, body: str, reply_to: str | None = None) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body[:MAX_BODY_CHARS]},
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        r = self._http.post(f"{self._base}/{self._phone_number_id}/messages", json=payload)
        if r.status_code >= 400:
            raise GraphError(f"send failed: HTTP {r.status_code}")

    def download_media(self, media_id: str, max_bytes: int) -> tuple[bytes, str | None]:
        """Look up the media URL by id, then download it with the same token."""
        meta = self._http.get(f"{self._base}/{media_id}")
        if meta.status_code >= 400:
            raise GraphError(f"media lookup failed: HTTP {meta.status_code}")
        info = meta.json()
        if int(info.get("file_size") or 0) > max_bytes:
            raise GraphError("media too large")
        with self._http.stream("GET", info["url"]) as r:
            if r.status_code >= 400:
                raise GraphError(f"media download failed: HTTP {r.status_code}")
            data = b""
            for chunk in r.iter_bytes():
                data += chunk
                if len(data) > max_bytes:
                    raise GraphError("media too large")
        return data, info.get("mime_type")
