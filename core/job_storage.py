"""Per-analysis storage and retention policies."""

from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_JOBS_DIR = ROOT / "downloads" / "jobs"
VECTOR_JOBS_DIR = ROOT / "vector_db" / "jobs"
RETENTION_DAYS = int(os.getenv("VECTOR_RETENTION_DAYS", "7"))


def create_job() -> tuple[str, Path, Path]:
    job_id = uuid.uuid4().hex
    audio_dir = AUDIO_JOBS_DIR / job_id
    vector_dir = VECTOR_JOBS_DIR / job_id
    audio_dir.mkdir(parents=True, exist_ok=False)
    vector_dir.mkdir(parents=True, exist_ok=False)
    return job_id, audio_dir, vector_dir


def cleanup_audio_job(audio_dir: Path) -> None:
    """Remove downloaded media and WAV chunks after processing."""
    shutil.rmtree(audio_dir, ignore_errors=True)


def cleanup_vector_job(vector_dir: Path) -> None:
    """Remove a vector store when a job never completed successfully."""
    shutil.rmtree(vector_dir, ignore_errors=True)


def cleanup_expired_vector_jobs() -> None:
    """Remove vector stores older than the configured retention period."""
    cutoff = time.time() - (RETENTION_DAYS * 24 * 60 * 60)
    VECTOR_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    for job_dir in VECTOR_JOBS_DIR.iterdir():
        if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
            shutil.rmtree(job_dir, ignore_errors=True)
