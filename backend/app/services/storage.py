import hashlib
from pathlib import Path

from app.config import settings


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def stored_relative_path(file_id: int, original_filename: str) -> str:
    safe_name = Path(original_filename).name or 'upload.csv'
    return f'uploads/{file_id}/{safe_name}'


def absolute_path(relative_path: str) -> Path:
    return settings.data_dir / relative_path


def write_upload(file_id: int, original_filename: str, content: bytes) -> str:
    ensure_data_dirs()
    relative = stored_relative_path(file_id, original_filename)
    target = absolute_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return relative


def delete_upload(relative_path: str) -> None:
    target = absolute_path(relative_path)
    if target.exists():
        target.unlink()
    parent = target.parent
    if parent.exists() and parent != settings.uploads_dir and not any(parent.iterdir()):
        parent.rmdir()
