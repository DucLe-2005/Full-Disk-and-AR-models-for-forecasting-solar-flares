import mimetypes
from pathlib import Path

from minio import Minio

from app.core.config import settings


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    found = client.bucket_exists(settings.minio_bucket)
    if not found:
        client.make_bucket(settings.minio_bucket)


def upload_file_to_minio(local_path: str | Path, object_name: str) -> str:
    local_path = Path(local_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"Artifact not found: {local_path}")

    client = get_minio_client()
    ensure_bucket_exists()

    content_type, _ = mimetypes.guess_type(local_path.name)
    client.fput_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        file_path=str(local_path),
        content_type=content_type or "application/octet-stream",
    )
    return object_name
