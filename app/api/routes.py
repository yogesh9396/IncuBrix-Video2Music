import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Header, Query, UploadFile, File, Response, status
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.models.schemas import (
    MusicJobRequest,
    JobStatusResponse,
    JobCreatedResponse,
    StemRegenerateRequest
)
from app.models.errors import IncuBrixError, ERR_JOB_NOT_FOUND
from app.tasks.job_manager import job_manager
from app.storage.storage_service import storage_service

router = APIRouter()


@router.post(
    "/music/jobs",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit background music generation job",
    description="Asynchronously queues an instrumental background music generation job."
)
async def create_music_job(
    request: MusicJobRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    provider: Optional[str] = Query(None, description="Optional override provider ('mock' or 'synth')")
):
    job = job_manager.create_job(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        provider_name=provider
    )
    return JobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message="Music generation job accepted and processing in background.",
        created_at=job.created_at
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get music generation job status",
    description="Polls current status, progress percentage (0-100), and result links."
)
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    return job.to_response()


@router.post(
    "/music/jobs/{job_id}/regenerate-stem",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate single instrument stem",
    description="Regenerates only the specified stem (e.g. 'drums') without altering any other stems."
)
async def regenerate_stem(
    job_id: str,
    request: StemRegenerateRequest,
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id")
):
    job = job_manager.regenerate_stem(job_id=job_id, stem_req=request, correlation_id=correlation_id)
    return JobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=f"Regenerating stem '{request.stem_name}' in background.",
        created_at=job.created_at
    )


@router.post(
    "/upload",
    summary="Upload voiceover / narration audio",
    description="Uploads narration audio to pass into music generation job."
)
async def upload_audio(file: UploadFile = File(...)):
    job_id = "uploads"
    filename = Path(file.filename).name
    save_path = storage_service.get_job_dir(job_id) / filename
    
    content = await file.read()
    save_path.write_bytes(content)
    
    return {
        "filename": filename,
        "local_path": str(save_path),
        "url": f"{settings.API_PREFIX}/artifacts/{job_id}/{filename}"
    }


@router.get(
    "/artifacts/{job_id}/{file_path:path}",
    summary="Download generated audio artifacts and manifest",
    description="Serves mix.wav, mix.mp3, stems/*.wav, mix_ducked.wav, and music_manifest.json."
)
async def get_artifact(job_id: str, file_path: str):
    target = storage_service.get_file_path(job_id, file_path)
    if not target.exists():
        raise IncuBrixError(
            code=ERR_JOB_NOT_FOUND,
            message=f"Artifact '{file_path}' for job '{job_id}' not found.",
            status_code=404
        )

    media_type = "application/octet-stream"
    if file_path.endswith(".wav"):
        media_type = "audio/wav"
    elif file_path.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif file_path.endswith(".json"):
        media_type = "application/json"

    return FileResponse(path=str(target), media_type=media_type, filename=target.name)
