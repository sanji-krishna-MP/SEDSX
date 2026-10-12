import os
import shutil
import time
import json
import uuid
import csv
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.models import RunConfig, ImageMetadata, RunSummary
import app.database as db
from app.metadata_parser import (
    parse_metadata_file,
    validate_metadata_against_image,
    to_image_metadata_dict
)
from app.image_processing import (
    decode_image_array,
    convert_to_float_grayscale,
    build_valid_mask,
    compute_preprocessing_metrics,
    extract_features_and_match,
    fit_robust_transformation,
    compute_comparison_metrics,
    render_visual_assets
)

router = APIRouter(prefix="/api")

RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "runs")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples")

# In-memory cancellation flags
CANCELLATION_FLAGS: Dict[str, bool] = {}

def execute_run(run_id: str, run_dir: str, config: RunConfig, metadata_src: Optional[ImageMetadata], metadata_ref: Optional[ImageMetadata], checkpoints_list: Optional[List[Dict[str, Any]]]):
    """Background worker pipeline executing all 12 stages described in Section 2 & 12 of the PRD."""
    t0 = time.time()
    timing: Dict[str, float] = {}
    warnings: List[str] = []

    try:
        # Check cancellation
        if CANCELLATION_FLAGS.get(run_id):
            db.update_run_status(run_id, "cancelled", "Cancelled by user")
            return

        # Stage 1: Validating
        db.update_run_status(run_id, "validating", "Decoding raster arrays and validating formats")
        src_path = os.path.join(run_dir, "source_original")
        ref_path = os.path.join(run_dir, "reference_original")

        src_raw = decode_image_array(src_path)
        ref_raw = decode_image_array(ref_path)

        timing["decoding"] = round((time.time() - t0) * 1000, 1)

        if src_raw.size == 0 or ref_raw.size == 0:
            raise ValueError("Decoded image array is empty.")

        h_s, w_s = src_raw.shape[:2]
        h_r, w_r = ref_raw.shape[:2]

        if CANCELLATION_FLAGS.get(run_id):
            db.update_run_status(run_id, "cancelled", "Cancelled by user")
            return

        # Stage 2: Preprocessing
        db.update_run_status(run_id, "preprocessing", "Computing float grayscale, masks and 9 preprocessing metrics")
        t_pre = time.time()

        src_gray = convert_to_float_grayscale(src_raw)
        ref_gray = convert_to_float_grayscale(ref_raw)

        src_user_mask = os.path.join(run_dir, "mask_source") if os.path.exists(os.path.join(run_dir, "mask_source")) else None
        ref_user_mask = os.path.join(run_dir, "mask_reference") if os.path.exists(os.path.join(run_dir, "mask_reference")) else None

        src_mask = build_valid_mask(src_raw, metadata_src, src_user_mask)
        ref_mask = build_valid_mask(ref_raw, metadata_ref, ref_user_mask)

        # Preprocessing metrics P1 to P9 for Source
        src_metrics, src_j = compute_preprocessing_metrics(
            src_raw, src_gray, src_mask, "source",
            config.intensity_bounds_source, config.dark_cutoff, metadata_src
        )

        # Preprocessing metrics P1 to P9 for Reference
        ref_metrics, ref_j = compute_preprocessing_metrics(
            ref_raw, ref_gray, ref_mask, "reference",
            config.intensity_bounds_reference, config.dark_cutoff, metadata_ref
        )

        timing["preprocessing"] = round((time.time() - t_pre) * 1000, 1)

        if CANCELLATION_FLAGS.get(run_id):
            db.update_run_status(run_id, "cancelled", "Cancelled by user")
            return

        # Stage 3: Matching
        db.update_run_status(run_id, "matching", "Extracting SIFT keypoints and generating one-to-one candidate pairs")
        t_match = time.time()

        src_kps, src_desc, ref_kps, ref_desc, candidates, Ns, Nr = extract_features_and_match(
            src_j, ref_j, src_mask, ref_mask, config
        )

        timing["matching"] = round((time.time() - t_match) * 1000, 1)

        if CANCELLATION_FLAGS.get(run_id):
            db.update_run_status(run_id, "cancelled", "Cancelled by user")
            return

        # Stage 4: Fitting
        db.update_run_status(run_id, "fitting", "Evaluating support gates, fitting robust affine model and verifying inliers")
        t_fit = time.time()

        affine_mat, candidates, nin, med_res, affine_params, gate_warnings = fit_robust_transformation(
            candidates, config, src_dims=(h_s, w_s), ref_dims=(h_r, w_r)
        )
        timing["fitting"] = round((time.time() - t_fit) * 1000, 1)

        status_result = "completed"
        if affine_mat is None:
            status_result = "inconclusive"
            warnings.extend(gate_warnings)
            if not gate_warnings:
                warnings.append(f"Inconclusive — insufficient reliable matches (inliers < {config.min_inliers}).")

        # Stage 5: Evaluating Comparison Metrics
        db.update_run_status(run_id, "evaluating", "Calculating 11 comparison metrics and spatial coverage")
        t_eval = time.time()

        comp_metrics, warped_src_mask, usable_overlap, overlap_bbox = compute_comparison_metrics(
            (h_s, w_s), (h_r, w_r),
            src_mask, ref_mask,
            affine_mat, candidates, nin, med_res,
            Ns, Nr, config,
            checkpoints=checkpoints_list,
            src_meta=metadata_src,
            ref_meta=metadata_ref
        )

        timing["evaluating"] = round((time.time() - t_eval) * 1000, 1)

        # Stage 6: Rendering Visual Assets
        db.update_run_status(run_id, "saving", "Rendering registered visualizations and persisting records")
        t_assets = time.time()

        assets = render_visual_assets(
            run_dir, src_gray, ref_gray, src_j, ref_j,
            src_mask, ref_mask, affine_mat, candidates, usable_overlap
        )
        timing["assets"] = round((time.time() - t_assets) * 1000, 1)
        timing["total"] = round((time.time() - t0) * 1000, 1)

        # Combine all metrics
        all_metrics_dict = [m.model_dump() for m in src_metrics + ref_metrics + comp_metrics]

        # Persist to SQLite
        db.save_metrics(run_id, all_metrics_dict)
        db.save_matches(run_id, candidates)
        if checkpoints_list:
            db.save_checkpoints(run_id, checkpoints_list)

        stage_msg = "Run finished successfully" if status_result == "completed" else "Inconclusive — insufficient reliable matches"
        failure_reason = gate_warnings[0] if (gate_warnings and status_result == "inconclusive") else (warnings[0] if (warnings and status_result == "inconclusive") else None)
        run_summary = {
            "id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": status_result,
            "stage_message": stage_msg,
            "timing_ms": timing,
            "source_dims": [h_s, w_s],
            "ref_dims": [h_r, w_r],
            "modes": ["image"] + (["geospatial"] if (metadata_src and metadata_src.gsd_m) else []),
            "warnings": warnings,
            "inlier_count": nin,
            "candidate_count": len(candidates),
            "median_residual": med_res,
            "overlap_bbox": overlap_bbox,
            "affine_params": affine_params,
            "failure_reason": failure_reason,
            "config": config.model_dump()
        }
        db.save_run(run_summary)

    except Exception as e:
        timing["total"] = round((time.time() - t0) * 1000, 1)
        warnings.append(str(e))
        db.save_run({
            "id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "stage_message": f"Processing failed: {str(e)}",
            "timing_ms": timing,
            "warnings": warnings
        })

@router.post("/metadata/parse")
async def parse_metadata_endpoint(
    file: UploadFile = File(...),
    expected_role: str = Form("source"),
    image_filename: Optional[str] = Form(None),
    image_width: Optional[int] = Form(None),
    image_height: Optional[int] = Form(None)
):
    """POST /api/metadata/parse: Streaming parser and validator for .xml, .lbl, and .json metadata."""
    try:
        content = await file.read()
        extracted = parse_metadata_file(file.filename or "metadata", content)
        status, status_label, checks = validate_metadata_against_image(
            extracted,
            expected_role=expected_role,
            image_filename=image_filename,
            image_width=image_width,
            image_height=image_height
        )
        return {
            "status": status,
            "status_label": status_label,
            "checks": checks,
            "metadata": {
                "product_id": extracted.get("product_id"),
                "instrument_id": extracted.get("instrument_id"),
                "acquisition_time": extracted.get("acquisition_time"),
                "image_filename": extracted.get("image_filename"),
                "width": extracted.get("width"),
                "height": extracted.get("height"),
                "pixel_data_type": extracted.get("pixel_data_type"),
                "resolution": extracted.get("resolution"),
            },
            "format": extracted.get("format"),
            "filename": file.filename,
            "size_bytes": len(content),
            "raw_fields": extracted.get("raw_fields", {}),
            "normalized_metadata": to_image_metadata_dict(extracted)
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "Invalid Metadata",
                "status_label": f"Parsing failed: {str(e)}",
                "checks": {"valid": False, "mismatches": [str(e)]},
                "metadata": {},
                "filename": file.filename,
                "size_bytes": 0
            }
        )

@router.post("/runs")
async def create_run(
    background_tasks: BackgroundTasks,
    source_file: UploadFile = File(...),
    reference_file: UploadFile = File(...),
    metadata_source: Optional[str] = Form(None),
    metadata_reference: Optional[str] = Form(None),
    metadata_source_file: Optional[UploadFile] = File(None),
    metadata_reference_file: Optional[UploadFile] = File(None),
    mask_source: Optional[UploadFile] = File(None),
    mask_reference: Optional[UploadFile] = File(None),
    checkpoints_file: Optional[UploadFile] = File(None),
    config_json: Optional[str] = Form(None)
):
    """POST /api/runs: Uploads images, optional metadata/masks/checkpoints, and queues background job."""
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Save uploaded images
    src_path = os.path.join(run_dir, "source_original")
    with open(src_path, "wb") as f:
        shutil.copyfileobj(source_file.file, f)

    ref_path = os.path.join(run_dir, "reference_original")
    with open(ref_path, "wb") as f:
        shutil.copyfileobj(reference_file.file, f)

    # Save optional masks
    if mask_source:
        with open(os.path.join(run_dir, "mask_source"), "wb") as f:
            shutil.copyfileobj(mask_source.file, f)

    if mask_reference:
        with open(os.path.join(run_dir, "mask_reference"), "wb") as f:
            shutil.copyfileobj(mask_reference.file, f)

    # Parse config
    config = RunConfig()
    if config_json:
        try:
            cfg_dict = json.loads(config_json)
            config = RunConfig(**cfg_dict)
        except Exception:
            pass

    # Parse metadata (from JSON string or uploaded metadata file)
    src_meta = None
    if metadata_source:
        try:
            src_meta = ImageMetadata(**json.loads(metadata_source))
        except Exception:
            pass
    elif metadata_source_file:
        try:
            raw_c = await metadata_source_file.read()
            with open(os.path.join(run_dir, "metadata_source_raw"), "wb") as f:
                f.write(raw_c)
            parsed = parse_metadata_file(metadata_source_file.filename or "meta", raw_c)
            src_meta = ImageMetadata(**to_image_metadata_dict(parsed))
        except Exception:
            pass

    ref_meta = None
    if metadata_reference:
        try:
            ref_meta = ImageMetadata(**json.loads(metadata_reference))
        except Exception:
            pass
    elif metadata_reference_file:
        try:
            raw_c = await metadata_reference_file.read()
            with open(os.path.join(run_dir, "metadata_reference_raw"), "wb") as f:
                f.write(raw_c)
            parsed = parse_metadata_file(metadata_reference_file.filename or "meta", raw_c)
            ref_meta = ImageMetadata(**to_image_metadata_dict(parsed))
        except Exception:
            pass

    # Parse checkpoints CSV if provided
    checkpoints_list = []
    if checkpoints_file:
        cp_path = os.path.join(run_dir, "checkpoints.csv")
        with open(cp_path, "wb") as f:
            shutil.copyfileobj(checkpoints_file.file, f)

        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    checkpoints_list.append({
                        "checkpoint_id": row.get("checkpoint_id", f"CP_{len(checkpoints_list)+1}"),
                        "source_x": float(row["source_x"]),
                        "source_y": float(row["source_y"]),
                        "ref_x": float(row["reference_x"]),
                        "ref_y": float(row["reference_y"]),
                        "pred_ref_x": None,
                        "pred_ref_y": None,
                        "residual": None
                    })
        except Exception:
            pass

    # Initial Run record in DB
    initial_run = {
        "id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "stage_message": "Comparison job queued",
        "source_filename": source_file.filename,
        "reference_filename": reference_file.filename,
        "modes": ["image"],
        "warnings": [],
        "config": config.model_dump()
    }
    db.save_run(initial_run)

    # Launch background job
    CANCELLATION_FLAGS[run_id] = False
    background_tasks.add_task(
        execute_run, run_id, run_dir, config, src_meta, ref_meta, checkpoints_list
    )

    return {"id": run_id, "status": "queued", "message": "Run created and queued successfully"}

@router.post("/runs/demo")
async def create_demo_run(background_tasks: BackgroundTasks):
    """Loads realistic bundled lunar demo data and runs the comparison immediately."""
    if not os.path.exists(os.path.join(SAMPLES_DIR, "source_OHRC.png")):
        from app.sample_generator import create_sample_dataset
        create_sample_dataset(SAMPLES_DIR)

    run_id = f"demo_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Copy demo assets
    shutil.copy(os.path.join(SAMPLES_DIR, "source_OHRC.png"), os.path.join(run_dir, "source_original"))
    shutil.copy(os.path.join(SAMPLES_DIR, "reference_LRO_NAC.png"), os.path.join(run_dir, "reference_original"))

    # Load metadata
    with open(os.path.join(SAMPLES_DIR, "metadata_source.json"), "r") as f:
        src_meta = ImageMetadata(**json.load(f))
    with open(os.path.join(SAMPLES_DIR, "metadata_reference.json"), "r") as f:
        ref_meta = ImageMetadata(**json.load(f))

    # Load checkpoints
    checkpoints_list = []
    with open(os.path.join(SAMPLES_DIR, "checkpoints.csv"), "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            checkpoints_list.append({
                "checkpoint_id": row["checkpoint_id"],
                "source_x": float(row["source_x"]),
                "source_y": float(row["source_y"]),
                "ref_x": float(row["reference_x"]),
                "ref_y": float(row["reference_y"]),
                "pred_ref_x": None,
                "pred_ref_y": None,
                "residual": None
            })

    config = RunConfig(error_scale_e0=1.0, error_scale_r0=1.0)

    initial_run = {
        "id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "stage_message": "Demonstration lunar comparison queued",
        "source_filename": "source_OHRC.png",
        "reference_filename": "reference_LRO_NAC.png",
        "modes": ["image", "geospatial"],
        "warnings": [],
        "config": config.model_dump()
    }
    db.save_run(initial_run)

    CANCELLATION_FLAGS[run_id] = False
    background_tasks.add_task(
        execute_run, run_id, run_dir, config, src_meta, ref_meta, checkpoints_list
    )

    return {"id": run_id, "status": "queued", "message": "Demo run initialized"}

@router.get("/runs")
async def get_runs_list(limit: int = 50):
    """GET /api/runs: List saved comparison runs."""
    runs = db.list_runs(limit=limit)
    return {"runs": runs}

@router.get("/runs/{run_id}")
async def get_run_details(run_id: str):
    """GET /api/runs/{id}: Return run stage, status, modes, warnings, and summary."""
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check what assets exist on disk
    run_dir = os.path.join(RUNS_DIR, run_id)
    assets = {}
    asset_names = [
        "source_original", "reference_original",
        "source_preprocessed.png", "reference_preprocessed.png",
        "source_mask.png", "reference_mask.png",
        "warped_source.png", "appearance_diff.png",
        "reference_zoomed.png", "warped_source_zoomed.png",
        "matches_visualization.png", "residuals_map.png"
    ]
    for an in asset_names:
        if os.path.exists(os.path.join(run_dir, an)):
            assets[an.split(".")[0]] = f"/api/runs/{run_id}/assets/{an}"

    return {"run": run, "assets": assets}

@router.get("/runs/{run_id}/metrics")
async def get_metrics(run_id: str):
    """GET /api/runs/{id}/metrics: Return all 9 per-image and 11 pair metric records."""
    metrics = db.get_run_metrics(run_id)
    return {"run_id": run_id, "metrics": metrics}

@router.get("/runs/{run_id}/matches")
async def get_matches(run_id: str, limit: int = 1000, offset: int = 0):
    """GET /api/runs/{id}/matches: Return match coordinates, inlier flags and residuals."""
    matches = db.get_run_matches(run_id, limit=limit, offset=offset)
    checkpoints = db.get_run_checkpoints(run_id)
    return {
        "run_id": run_id,
        "matches_count": len(matches),
        "matches": matches,
        "checkpoints": checkpoints
    }

@router.get("/runs/{run_id}/assets/{asset_name}")
async def get_run_asset(run_id: str, asset_name: str):
    """GET /api/runs/{id}/assets/{name}: Serves allowlisted assets."""
    # Prevent directory traversal
    safe_name = os.path.basename(asset_name)
    file_path = os.path.join(RUNS_DIR, run_id, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")
    return FileResponse(file_path)

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """POST /api/runs/{id}/cancel: Stop pending work and retain stage diagnostics."""
    CANCELLATION_FLAGS[run_id] = True
    db.update_run_status(run_id, "cancelled", "Run cancelled by user request")
    return {"message": f"Run {run_id} marked as cancelled"}
