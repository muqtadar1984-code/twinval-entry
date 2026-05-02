"""
S3-compatible photo storage (Cloudflare R2 by default).

In dev or test environments without S3 creds, the upload is short-circuited
to a synthetic local URL so the rest of the flow keeps working — production
deployments must set S3_ENDPOINT_URL and credentials.
"""

from __future__ import annotations

import io
import logging
import secrets
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

log = logging.getLogger(__name__)


class PhotoValidationError(ValueError):
    pass


@dataclass
class UploadResult:
    public_url: str
    key: str
    bytes_written: int


def validate_photo(content: bytes, content_type: str) -> None:
    settings = get_settings()
    if content_type not in settings.allowed_photo_mime_types_list:
        raise PhotoValidationError(
            f"unsupported mime type: {content_type}. "
            f"allowed: {settings.allowed_photo_mime_types_list}"
        )
    if len(content) > settings.max_photo_bytes:
        raise PhotoValidationError(
            f"photo too large: {len(content)} bytes "
            f"(max {settings.max_photo_bytes})"
        )
    if len(content) == 0:
        raise PhotoValidationError("empty photo")


_MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}


def _make_key(content_type: str) -> str:
    ext = _MIME_EXT.get(content_type, "bin")
    return f"observations/{secrets.token_urlsafe(16)}.{ext}"


def upload_photo(content: bytes, content_type: str) -> UploadResult:
    """
    Upload a validated photo blob to S3-compatible storage and return the
    public URL. In dev/test (no S3 endpoint configured) returns a synthetic
    local URL so the call site behaves identically.
    """
    validate_photo(content, content_type)

    settings = get_settings()
    key = _make_key(content_type)

    if not settings.s3_endpoint_url or not settings.s3_bucket:
        log.warning(
            "S3 not configured — photo upload short-circuited to local stub URL "
            "(set S3_ENDPOINT_URL and S3_BUCKET to enable real uploads)"
        )
        return UploadResult(
            public_url=f"local-stub://photos/{key}",
            key=key,
            bytes_written=len(content),
        )

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )

    try:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=io.BytesIO(content),
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as e:
        log.error("S3 upload failed: %s", e)
        raise

    base = settings.s3_public_base_url.rstrip("/") if settings.s3_public_base_url else (
        f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}"
    )
    return UploadResult(
        public_url=f"{base}/{key}",
        key=key,
        bytes_written=len(content),
    )
