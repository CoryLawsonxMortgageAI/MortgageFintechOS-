"""Google Drive integration client for MortgageFintechOS.

Provides async Google Drive API v3 operations for listing, downloading,
and importing documents from Drive folders using service account auth.
"""

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()

DRIVE_API = "https://www.googleapis.com/drive/v3"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GDriveClient:
    """Async Google Drive API v3 client using service account JWT auth."""

    def __init__(self, service_account_json: str, folder_id: str = ""):
        self._folder_id = folder_id
        self._sa_path = service_account_json
        self._access_token: str = ""
        self._token_expiry: datetime | None = None
        self._log = logger.bind(component="gdrive")

    async def _ensure_token(self) -> str:
        """Get or refresh access token via service account JWT."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            creds = service_account.Credentials.from_service_account_file(
                self._sa_path, scopes=SCOPES
            )
            creds.refresh(Request())
            self._access_token = creds.token
            self._token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
            self._log.info("drive_token_refreshed")
            return self._access_token
        except Exception as e:
            self._log.error("drive_auth_failed", error=str(e))
            raise

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def list_files(
        self,
        folder_id: str = "",
        mime_filter: str = "",
        page_size: int = 100,
    ) -> dict[str, Any]:
        """List files in a Drive folder."""
        fid = folder_id or self._folder_id
        if not fid:
            return {"error": "No folder_id configured", "files": []}

        token = await self._ensure_token()
        query = f"'{fid}' in parents and trashed = false"
        if mime_filter:
            query += f" and mimeType = '{mime_filter}'"

        params = {
            "q": query,
            "pageSize": page_size,
            "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink)",
            "orderBy": "modifiedTime desc",
        }

        async with aiohttp.ClientSession(headers=self._headers(token)) as session:
            async with session.get(f"{DRIVE_API}/files", params=params) as resp:
                data = await resp.json()
                if resp.status == 200:
                    files = data.get("files", [])
                    self._log.info("drive_files_listed", folder=fid[:8], count=len(files))
                    return {"files": files, "count": len(files)}
                else:
                    self._log.error("drive_list_failed", status=resp.status, error=str(data)[:200])
                    return {"error": str(data)[:200], "status": resp.status, "files": []}

    async def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        """Get file metadata."""
        token = await self._ensure_token()
        params = {"fields": "id,name,mimeType,size,modifiedTime,webViewLink,parents"}

        async with aiohttp.ClientSession(headers=self._headers(token)) as session:
            async with session.get(f"{DRIVE_API}/files/{file_id}", params=params) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return data
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    async def download_file(self, file_id: str) -> dict[str, Any]:
        """Download file content as bytes."""
        token = await self._ensure_token()

        async with aiohttp.ClientSession(headers=self._headers(token)) as session:
            # First get metadata to know the type
            meta = await self.get_file_metadata(file_id)
            mime = meta.get("mimeType", "")
            name = meta.get("name", file_id)

            # Google Docs/Sheets need export, regular files use alt=media
            if mime.startswith("application/vnd.google-apps."):
                return await self.export_google_doc(file_id, "text/plain")

            async with session.get(f"{DRIVE_API}/files/{file_id}", params={"alt": "media"}) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    self._log.info("drive_file_downloaded", file=name, size=len(content))
                    return {
                        "name": name,
                        "mime_type": mime,
                        "size": len(content),
                        "content": content,
                    }
                else:
                    error = await resp.text()
                    return {"error": error[:200], "status": resp.status}

    async def export_google_doc(
        self, file_id: str, mime_type: str = "text/plain"
    ) -> dict[str, Any]:
        """Export a Google Doc/Sheet as the specified MIME type."""
        token = await self._ensure_token()
        params = {"mimeType": mime_type}

        async with aiohttp.ClientSession(headers=self._headers(token)) as session:
            async with session.get(f"{DRIVE_API}/files/{file_id}/export", params=params) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    self._log.info("drive_doc_exported", file_id=file_id[:8], mime=mime_type)
                    return {"content": content, "mime_type": mime_type, "size": len(content)}
                else:
                    error = await resp.text()
                    return {"error": error[:200], "status": resp.status}

    async def import_folder(self, folder_id: str = "") -> dict[str, Any]:
        """Import all files from a folder — returns metadata list for classification."""
        listing = await self.list_files(folder_id=folder_id)
        if "error" in listing and listing.get("status"):
            return listing

        imported = []
        for f in listing.get("files", []):
            imported.append({
                "file_id": f["id"],
                "name": f["name"],
                "mime_type": f.get("mimeType", ""),
                "size": f.get("size", "0"),
                "modified": f.get("modifiedTime", ""),
                "link": f.get("webViewLink", ""),
            })

        self._log.info("drive_folder_imported", count=len(imported))
        return {"files": imported, "count": len(imported), "folder_id": folder_id or self._folder_id}
