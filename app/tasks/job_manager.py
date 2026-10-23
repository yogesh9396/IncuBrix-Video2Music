import asyncio
import hashlib
import hmac
import json
import logging
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import numpy as np
import requests

from app.config import settings
from app.models.schemas import (
    MusicJobRequest,
    JobStatusResponse,
    JobResultFiles,
    MusicManifest,
    StemRegenerateRequest
)
from app.models.errors import IncuBrixError, ERR_JOB_NOT_FOUND, ERR_IDEMPOTENCY_CONFLICT, ERR_INVALID_STEM
from app.engine.generator import generator
from app.storage.storage_service import storage_service
from app.logging_config import job_id_ctx, correlation_id_ctx

logger = logging.getLogger(__name__)


class JobRecord:
    def __init__(self, job_id: str, request: MusicJobRequest, idempotency_key: Optional[str] = None):
        self.job_id = job_id
        self.request = request
        self.idempotency_key = idempotency_key
        self.status = "queued"  # queued, running, succeeded, failed
        self.progress = 0
        now_str = datetime.now(timezone.utc).isoformat()
        self.created_at = now_str
        self.updated_at = now_str
        self.result: Optional[JobResultFiles] = None
        self.manifest: Optional[MusicManifest] = None
        self.error: Optional[Dict[str, Any]] = None
        self.stems_cache: Optional[Dict[str, np.ndarray]] = None

    def to_response(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            created_at=self.created_at,
            updated_at=self.updated_at,
            result=self.result,
            manifest=self.manifest,
            error=self.error
        )


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobRecord] = {}
        self.idempotency_map: Dict[str, Tuple[str, str]] = {}  # key -> (job_id, request_hash)
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS, thread_name_prefix="music-worker")

    def _hash_request(self, request: MusicJobRequest) -> str:
        data_str = request.model_dump_json(exclude={"callback_url"})
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def create_job(
        self,
        request: MusicJobRequest,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> JobRecord:
        with self.lock:
            # Check idempotency
            if idempotency_key:
                req_hash = self._hash_request(request)
                if idempotency_key in self.idempotency_map:
                    existing_id, stored_hash = self.idempotency_map[idempotency_key]
                    if req_hash != stored_hash:
                        raise IncuBrixError(
                            code=ERR_IDEMPOTENCY_CONFLICT,
                            message=f"Idempotency key '{idempotency_key}' already used with different request parameters.",
                            status_code=409
                        )
                    # Return existing job
                    logger.info(f"Idempotency hit for key '{idempotency_key}': returning job {existing_id}")
                    return self.jobs[existing_id]

            job_id = str(uuid.uuid4())
            job = JobRecord(job_id=job_id, request=request, idempotency_key=idempotency_key)
            self.jobs[job_id] = job
            if idempotency_key:
                self.idempotency_map[idempotency_key] = (job_id, self._hash_request(request))

        # Schedule worker execution
        self.executor.submit(self._run_job, job_id, provider_name, correlation_id)
        return job

    def get_job(self, job_id: str) -> JobRecord:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                # Try loading from disk storage
                job_state_file = storage_service.get_file_path(job_id, "job_state.json")
                if job_state_file.exists():
                    try:
                        data = json.loads(job_state_file.read_text(encoding="utf-8"))
                        req = MusicJobRequest(**data["request"])
                        job = JobRecord(job_id=job_id, request=req, idempotency_key=data.get("idempotency_key"))
                        job.status = data["status"]
                        job.progress = data["progress"]
                        job.created_at = data["created_at"]
                        job.updated_at = data["updated_at"]
                        if data.get("result"):
                            job.result = JobResultFiles(**data["result"])
                        if data.get("manifest"):
                            job.manifest = MusicManifest(**data["manifest"])
                        if data.get("error"):
                            job.error = data["error"]
                        self.jobs[job_id] = job
                    except Exception as e:
                        logger.error(f"Failed to restore job state for {job_id}: {e}")

            if not job:
                raise IncuBrixError(
                    code=ERR_JOB_NOT_FOUND,
                    message=f"Job with id '{job_id}' not found.",
                    status_code=404
                )
            return job

    def _persist_job_state(self, job: JobRecord):
        job_dir = storage_service.get_job_dir(job.job_id)
        state_path = job_dir / "job_state.json"
        state_data = {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "idempotency_key": job.idempotency_key,
            "request": job.request.model_dump(),
            "result": job.result.model_dump() if job.result else None,
            "manifest": job.manifest.model_dump() if job.manifest else None,
            "error": job.error
        }
        try:
            state_path.write_text(json.dumps(state_data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist job state to disk: {e}")

    def _run_job(
        self,
        job_id: str,
        provider_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        regenerate_stem: Optional[str] = None
    ):
        # Set context variables for logs in this worker thread
        job_id_ctx.set(job_id)
        correlation_id_ctx.set(correlation_id)

        job = self.jobs[job_id]
        job.status = "running"
        job.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist_job_state(job)
        logger.info(f"Job {job_id} started execution")

        def progress_cb(pct: int):
            job.progress = pct
            job.updated_at = datetime.now(timezone.utc).isoformat()

        try:
            result_files, manifest, stems_cache = generator.process_job(
                job_id=job_id,
                request=job.request,
                provider_name=provider_name,
                regenerate_stem=regenerate_stem,
                existing_stems=job.stems_cache,
                progress_callback=progress_cb
            )

            job.status = "succeeded"
            job.progress = 100
            job.result = result_files
            job.manifest = manifest
            job.stems_cache = stems_cache
            job.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_job_state(job)
            logger.info(f"Job {job_id} completed successfully")

            # Fire webhook if callback_url configured
            if job.request.callback_url:
                self._send_callback(job)

        except Exception as e:
            logger.exception(f"Job {job_id} execution failed: {e}")
            job.status = "failed"
            job.updated_at = datetime.now(timezone.utc).isoformat()
            job.error = {
                "code": getattr(e, "code", "INTERNAL_SERVER_ERROR"),
                "message": str(e),
                "retryable": getattr(e, "retryable", False),
                "details": getattr(e, "details", None)
            }
            self._persist_job_state(job)
            if job.request.callback_url:
                self._send_callback(job)

    def regenerate_stem(
        self,
        job_id: str,
        stem_req: StemRegenerateRequest,
        correlation_id: Optional[str] = None
    ) -> JobRecord:
        job = self.get_job(job_id)
        if job.status != "succeeded":
            raise IncuBrixError(
                code="INVALID_JOB_STATE",
                message=f"Job {job_id} must be in succeeded state to regenerate stems (current: {job.status}).",
                status_code=400
            )

        stem_name = stem_req.stem_name.lower()
        if stem_name not in ["drums", "bass", "chords", "melody"]:
            raise IncuBrixError(
                code=ERR_INVALID_STEM,
                message=f"Stem '{stem_name}' is not recognized. Valid stems: drums, bass, chords, melody.",
                status_code=400
            )

        # Update seed for stem if given
        if stem_req.seed is not None:
            job.request.seed = stem_req.seed
        else:
            job.request.seed = (job.request.seed or settings.SEED_DEFAULT) + random.randint(100, 9999)

        job.status = "queued"
        job.progress = 0
        job.updated_at = datetime.now(timezone.utc).isoformat()

        # Submit stem regeneration task
        self.executor.submit(self._run_job, job_id, None, correlation_id, stem_name)
        return job

    def _send_callback(self, job: JobRecord):
        """
        Sends an HTTP POST webhook to callback_url, signed with HMAC-SHA256
        in X-IncuBrix-Signature header.
        """
        url = job.request.callback_url
        if not url:
            return

        payload = job.to_response().model_dump_json()
        signature = hmac.new(
            settings.WEBHOOK_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": f"sha256={signature}"
        }

        try:
            logger.info(f"Sending webhook callback for job {job.job_id} to {url}")
            requests.post(url, data=payload, headers=headers, timeout=settings.WEBHOOK_TIMEOUT_S)
        except Exception as e:
            logger.warning(f"Failed to deliver callback to {url}: {e}")


job_manager = JobManager()
