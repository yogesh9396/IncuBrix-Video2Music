#!/usr/bin/env python3
"""
IncuBrix Batch Runner CLI
Runs a folder or JSON file of test inputs against the IncuBrix AI Background Music API
and writes all results (mix, stems, manifest, logs) to a designated output folder.

Usage:
    python scripts/batch_runner.py --input-path test_pack/inputs --output-dir test_pack/outputs --api-url http://localhost:8000
    or directly in-process via:
    python scripts/batch_runner.py --input-path test_pack/inputs --output-dir test_pack/outputs --in-process
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import MusicJobRequest
from app.engine.generator import generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_runner")


def run_single_in_process(request_data: Dict[str, Any], output_job_dir: Path, job_index: int) -> Dict[str, Any]:
    job_id = f"batch_job_{job_index:03d}_{int(time.time())}"
    logger.info(f"Processing in-process job {job_id}: '{request_data.get('prompt')}' ({request_data.get('duration_s')}s)")

    req = MusicJobRequest(**request_data)
    start_t = time.time()
    
    result_files, manifest, stems_cache = generator.process_job(
        job_id=job_id,
        request=req,
        provider_name="synth"
    )
    elapsed = round(time.time() - start_t, 3)

    # Copy files into output_job_dir
    import shutil
    from app.storage.storage_service import storage_service
    src_dir = storage_service.get_job_dir(job_id)
    if src_dir.exists():
        for item in src_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, output_job_dir / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, output_job_dir / item.name)

    logger.info(f"Job {job_id} completed in {elapsed}s. Output saved to {output_job_dir}")
    return {
        "job_id": job_id,
        "status": "succeeded",
        "elapsed_s": elapsed,
        "manifest": manifest.model_dump()
    }


def run_batch(input_path: Path, output_dir: Path, api_url: Optional[str] = None, in_process: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_files = []
    if input_path.is_file():
        input_files = [input_path]
    elif input_path.is_dir():
        input_files = sorted(list(input_path.glob("*.json")))

    if not input_files:
        logger.error(f"No JSON test files found at {input_path}")
        return

    logger.info(f"Found {len(input_files)} test input files to process")
    summary = []

    for idx, f_path in enumerate(input_files, 1):
        try:
            content = json.loads(f_path.read_text(encoding="utf-8"))
            items = content if isinstance(content, list) else [content]
            
            for sub_idx, item in enumerate(items, 1):
                case_name = f"{f_path.stem}_{sub_idx}" if len(items) > 1 else f_path.stem
                case_out_dir = output_dir / case_name
                case_out_dir.mkdir(parents=True, exist_ok=True)

                if in_process:
                    res = run_single_in_process(item, case_out_dir, idx * 10 + sub_idx)
                    summary.append({
                        "case": case_name,
                        "status": "succeeded",
                        "duration_s": item.get("duration_s"),
                        "elapsed_s": res["elapsed_s"],
                        "lufs": res["manifest"]["loudness"]["mix_integrated_lufs"],
                        "true_peak_dbtp": res["manifest"]["loudness"]["mix_true_peak_dbtp"],
                        "reconstruction_error_db": res["manifest"]["loudness"]["reconstruction_error_db"]
                    })
                else:
                    # HTTP API call
                    url = f"{api_url.rstrip('/')}/api/v1/music/jobs"
                    headers = {"Idempotency-Key": f"batch-{case_name}"}
                    post_res = requests.post(url, json=item, headers=headers)
                    if post_res.status_code != 202:
                        logger.error(f"Failed to submit {case_name}: {post_res.text}")
                        summary.append({"case": case_name, "status": "failed", "error": post_res.text})
                        continue
                    
                    job_id = post_res.json()["job_id"]
                    # Poll
                    start_poll = time.time()
                    while time.time() - start_poll < 60:
                        poll = requests.get(f"{api_url.rstrip('/')}/api/v1/jobs/{job_id}").json()
                        if poll["status"] in ["succeeded", "failed"]:
                            break
                        time.sleep(0.5)

                    summary.append({"case": case_name, "status": poll["status"], "job_id": job_id})

        except Exception as e:
            logger.exception(f"Error processing test file {f_path}: {e}")
            summary.append({"case": f_path.name, "status": "error", "error": str(e)})

    # Write summary report
    summary_file = output_dir / "batch_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(f"Batch run finished! Summary written to {summary_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncuBrix Batch Test Runner")
    parser.add_argument("--input-path", type=str, default="test_pack/inputs", help="Path to input JSON file or folder")
    parser.add_argument("--output-dir", type=str, default="test_pack/outputs", help="Directory to save generated outputs")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="Base URL of running API")
    parser.add_argument("--in-process", action="store_true", default=True, help="Run generator in-process directly")

    args = parser.parse_args()
    run_batch(Path(args.input_path), Path(args.output_dir), args.api_url, args.in_process)
