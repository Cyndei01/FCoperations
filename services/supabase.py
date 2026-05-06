from __future__ import annotations

import os
import re
import json
from io import BytesIO
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

from app_config import SUPABASE


REQUEST_TIMEOUT_SECONDS = 20


def supabase_config_status() -> dict[str, Any]:
    return {
        "configured": supabase_ready(),
        "url": bool(_url()),
        "service_role_key": bool(_service_role_key()),
        "anon_key": bool(_anon_key()),
        "bucket": _bucket_name(),
    }


def supabase_ready() -> bool:
    return bool(_url() and _api_key())


def test_supabase_connection() -> tuple[bool, str]:
    if not supabase_ready():
        return False, "Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY."

    try:
        response = requests.get(
            f"{_url()}/storage/v1/bucket",
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return False, f"Supabase connection failed: {error}"

    buckets = response.json()
    bucket_names = {bucket.get("name") for bucket in buckets if isinstance(bucket, dict)}
    bucket = _bucket_name()
    if bucket in bucket_names:
        return True, f"Connected to Supabase. Storage bucket '{bucket}' is available."
    if _service_role_key() and _create_bucket(bucket):
        return True, f"Connected to Supabase. Created storage bucket '{bucket}'."
    return True, f"Connected to Supabase. Storage bucket '{bucket}' was not found."


PARSED_LOAD_HISTORY_PATH = "parsed-load-history/latest.csv"
KNOWLEDGE_MANIFEST_PATH = "knowledge-files/manifest.json"


def upload_file(file_name: str, content: bytes, folder: str, object_path: str | None = None) -> tuple[bool, str]:
    if not supabase_ready():
        return False, "Supabase is not configured."

    bucket = _bucket_name()
    if not _ensure_bucket(bucket):
        return False, f"Supabase storage bucket '{bucket}' is not available."

    object_path = object_path or _object_path(file_name, folder)
    try:
        response = requests.post(
            f"{_url()}/storage/v1/object/{bucket}/{object_path}",
            headers={
                **_headers(),
                "Content-Type": "application/octet-stream",
                "x-upsert": "true",
            },
            data=content,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return False, f"Supabase upload failed: {error}"

    return True, object_path


def download_file(object_path: str) -> tuple[bool, bytes | str]:
    if not supabase_ready():
        return False, "Supabase is not configured."

    try:
        response = requests.get(
            f"{_url()}/storage/v1/object/{_bucket_name()}/{object_path}",
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return False, f"Supabase download failed: {error}"

    return True, response.content


def upload_parsed_load_history(loads) -> tuple[bool, str]:
    if loads is None or loads.empty:
        return False, "No parsed load history to save."
    csv_bytes = loads.to_csv(index=False).encode("utf-8")
    return upload_file("latest.csv", csv_bytes, "parsed-load-history", PARSED_LOAD_HISTORY_PATH)


def download_parsed_load_history():
    import pandas as pd

    ok, payload = download_file(PARSED_LOAD_HISTORY_PATH)
    if not ok:
        return None
    return pd.read_csv(BytesIO(payload))


def upload_knowledge_file(file_name: str, content: bytes) -> tuple[bool, str]:
    ok, object_path = upload_file(file_name, content, "knowledge-files")
    if not ok:
        return ok, object_path

    manifest = download_knowledge_manifest()
    record = {
        "name": file_name,
        "type": file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "",
        "size": len(content),
        "path": object_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest = [item for item in manifest if item.get("name") != file_name]
    manifest.append(record)
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_ok, manifest_message = upload_file(
        "manifest.json",
        manifest_bytes,
        "knowledge-files",
        KNOWLEDGE_MANIFEST_PATH,
    )
    if not manifest_ok:
        return False, manifest_message
    return True, object_path


def download_knowledge_manifest() -> list[dict[str, Any]]:
    ok, payload = download_file(KNOWLEDGE_MANIFEST_PATH)
    if not ok:
        return []
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _ensure_bucket(bucket: str) -> bool:
    if not supabase_ready():
        return False
    try:
        response = requests.get(
            f"{_url()}/storage/v1/bucket/{bucket}",
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return True
    except requests.RequestException:
        return False
    if _service_role_key():
        return _create_bucket(bucket)
    return False


def _create_bucket(bucket: str) -> bool:
    try:
        response = requests.post(
            f"{_url()}/storage/v1/bucket",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"id": bucket, "name": bucket, "public": False},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return response.status_code in {200, 201, 409}
    except requests.RequestException:
        return False


def _object_path(file_name: str, folder: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_folder = _safe_name(folder)
    safe_name = _safe_name(file_name)
    return f"{safe_folder}/{timestamp}-{uuid4().hex[:8]}-{safe_name}"


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "file"


def _headers() -> dict[str, str]:
    key = _api_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def _api_key() -> str:
    return _service_role_key() or _anon_key()


def _url() -> str:
    return _secret(SUPABASE["url_env"]).rstrip("/")


def _service_role_key() -> str:
    return _secret(SUPABASE["service_role_key_env"])


def _anon_key() -> str:
    return _secret(SUPABASE["anon_key_env"])


def _bucket_name() -> str:
    return _secret(SUPABASE["storage_bucket_env"], SUPABASE["default_storage_bucket"])


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default
