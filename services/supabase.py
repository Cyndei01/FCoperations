from __future__ import annotations

import os
import re
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


def upload_file(file_name: str, content: bytes, folder: str, object_path: str | None = None) -> tuple[bool, str]:
    if not supabase_ready():
        return False, "Supabase is not configured."

    bucket = _bucket_name()
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
