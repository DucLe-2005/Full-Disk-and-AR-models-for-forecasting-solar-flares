import logging
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.api.repositories.job_repository import JobRepository
from app.api.repositories.prediction_repository import PredictionRepository
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.schema import create_database_schema
from app.core.storage import upload_file_to_minio
from prediction.pipeline.run_pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_SECONDS = 5
ATTRIBUTION_METHOD_NAMES = {
    "guided_gradcam": "Guided Grad-CAM",
    "integrated_gradients": "Integrated Gradients",
    "deepshap": "DeepLiftShap",
    "consensus": "Consensus",
}


def _resolve_helioviewer_date(job_payload: dict | None) -> str:
    helioviewer_date = (
        (job_payload or {}).get("helioviewer_date")
        or settings.default_helioviewer_date
    )
    if not helioviewer_date:
        raise ValueError(
            "Missing helioviewer_date. Provide it in the queued job payload or "
            "set DEFAULT_HELIOVIEWER_DATE."
        )
    return helioviewer_date


def _format_helioviewer_date(value: datetime) -> str:
    return value.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _build_object_name(requested_at: datetime, category: str, artifact_path: str | Path) -> str:
    path = Path(artifact_path)
    hour = requested_at.replace(minute=0, second=0, microsecond=0)
    return (
        f"predictions/{hour.year}/{hour.month:02d}/{hour.day:02d}/"
        f"{hour.hour:02d}/{category}/{path.name}"
    )


def _upload_single_artifact(
    requested_at: datetime,
    category: str,
    artifact_path: str | None,
) -> str | None:
    if artifact_path is None:
        return None
    return upload_file_to_minio(
        artifact_path,
        _build_object_name(requested_at, category, artifact_path),
    )


def _upload_artifact_group(
    requested_at: datetime,
    category: str,
    artifact_dir: str | None,
    filename_prefix: str | None = None,
) -> list[str]:
    if artifact_dir is None:
        return []

    artifact_dir_path = Path(artifact_dir)
    if not artifact_dir_path.exists():
        return []

    uploaded_objects = []
    for file_path in sorted(path for path in artifact_dir_path.iterdir() if path.is_file()):
        if filename_prefix is not None and not file_path.name.startswith(filename_prefix):
            continue
        uploaded_objects.append(
            upload_file_to_minio(
                file_path,
                _build_object_name(requested_at, category, file_path),
            )
        )
    return uploaded_objects


def _find_uploaded_patch_object(
    saved_path: str | None,
    active_region_object_paths: list[str],
) -> str | None:
    if saved_path is None:
        return None

    patch_name = Path(saved_path).name
    return next(
        (
            object_path
            for object_path in active_region_object_paths
            if object_path.endswith(f"/{patch_name}")
        ),
        None,
    )


def _select_region_prediction(region: dict) -> dict:
    return (
        region.get("ar_predictions", {}).get("mobilenet")
        or next(
            (
                prediction
                for prediction in region.get("ar_predictions", {}).values()
                if "ar_prob" in prediction
            ),
            None,
        )
        or {}
    )


def _build_ar_patches(
    crop_results: list[dict],
    active_region_object_paths: list[str],
) -> list[dict]:
    active_regions = []
    for region in crop_results:
        model_prediction = _select_region_prediction(region)
        flare_probability = float(model_prediction.get("ar_prob", 0.0))

        active_regions.append(
            {
                "rank": region["region_index"],
                "probability": flare_probability,
                "heatmap_score": region.get("consensus_score"),
                "image_path": _find_uploaded_patch_object(
                    region.get("saved_path"),
                    active_region_object_paths,
                ),
                "bbox_original": list(region.get("bbox_original_xyxy", [])),
                "bbox_resized": list(region.get("bbox_resized_xyxy", [])),
                "center_original": list(region.get("center_original_xy", [])),
                "center_resized": list(region.get("center_resized_xy", [])),
                "polygon_original": region.get("polygon_original_xy", []),
                "polygon_resized": region.get("polygon_resized_xy", []),
                "crop_box_original": list(region.get("crop_box_original_xyxy", [])),
                "crop_box_clipped_original": list(region.get("crop_box_clipped_original_xyxy", [])),
                "crop_padding_ltrb": list(region.get("crop_padding_ltrb", [])),
                "proposal_score": region.get("proposal_score"),
                "consensus_score": region.get("consensus_score"),
                "area_weighted_score": region.get("area_weighted_score"),
                "area_resized": region.get("area_resized", region.get("area")),
                "ar_predictions": region.get("ar_predictions", {}),
            }
        )
    return active_regions


def _upload_pipeline_artifacts(requested_at: datetime, result: dict) -> dict:
    artifact_dirs = result.get("artifact_dirs", {})
    jp2_stem = Path(result["image_path"]).stem if result.get("image_path") else None
    active_region_debug = result.get("active_regions", {}).get("debug", {})
    attribution_map_paths = active_region_debug.get("attribution_map_paths", {})
    proposal_heatmap_path = active_region_debug.get("heatmap_path")
    final_hulls_path = active_region_debug.get("final_hulls_path")
    proposal_overlay_path = active_region_debug.get("proposal_overlay_path")

    jpg_object_path = _upload_single_artifact(
        requested_at,
        "full_disk",
        result.get("jpg_path"),
    )
    active_region_object_paths = _upload_artifact_group(
        requested_at,
        "active_regions",
        artifact_dirs.get("active_regions"),
        filename_prefix=jp2_stem,
    )
    final_hulls_object_path = _upload_single_artifact(
        requested_at,
        "heat_maps",
        final_hulls_path,
    )
    proposal_heatmap_object_path = _upload_single_artifact(
        requested_at,
        "heat_maps",
        proposal_heatmap_path,
    )
    proposal_overlay_object_path = _upload_single_artifact(
        requested_at,
        "heat_maps",
        proposal_overlay_path,
    )

    heatmaps = []
    for method_key, method_name in ATTRIBUTION_METHOD_NAMES.items():
        object_path = _upload_single_artifact(
            requested_at,
            "heat_maps",
            attribution_map_paths.get(method_key),
        )
        if object_path:
            heatmaps.append(
                {
                    "method_name": method_name,
                    "image_path": object_path,
                }
            )
    if final_hulls_object_path:
        heatmaps.append(
            {
                "method_name": "Final Region Hulls",
                "image_path": final_hulls_object_path,
            }
        )
    if proposal_heatmap_object_path:
        heatmaps.append(
            {
                "method_name": "Proposal Heatmap",
                "image_path": proposal_heatmap_object_path,
            }
        )
    if proposal_overlay_object_path:
        heatmaps.append(
            {
                "method_name": "Final Region Proposal",
                "image_path": proposal_overlay_object_path,
            }
        )

    return {
        "jp2_object_path": None,
        "full_disk_image_path": jpg_object_path,
        "heatmaps": heatmaps,
        "active_regions": _build_ar_patches(
            result["ar_region_crops"],
            active_region_object_paths,
        ),
    }


def _build_prediction_payload(prediction_id: str, result: dict) -> dict:
    requested_at = datetime.fromisoformat(result["prediction_datetime"])
    artifact_payload = _upload_pipeline_artifacts(requested_at, result)
    active_regions = artifact_payload["active_regions"]
    return {
        "id": prediction_id,
        "requested_at": requested_at,
        "global_flare_probability": float(result["prediction"]["p_flare"]),
        "predicted_class": int(result["prediction"]["pred_class"]),
        "localized_probabilities": [
            float(region["probability"])
            for region in active_regions
        ],
        **artifact_payload,
    }


def _run_pipeline_for_job(helioviewer_date: str) -> dict:
    return run_pipeline(helioviewer_date)


def _process_claimed_job(job_repo: JobRepository, prediction_repo: PredictionRepository, job) -> None:
    if job.requested_at is not None:
        requested_datetime = prediction_repo.normalize_requested_at(job.requested_at)
        helioviewer_date = _format_helioviewer_date(requested_datetime)
    else:
        helioviewer_date = _resolve_helioviewer_date(job.payload)
        requested_datetime = datetime.strptime(
            helioviewer_date.strip().replace("T", " ").replace("Z", ""),
            "%Y-%m-%d %H:%M:%S",
        )
        requested_datetime = prediction_repo.normalize_requested_at(requested_datetime)
    existing_prediction = prediction_repo.get_for_requested_at(requested_datetime)
    if existing_prediction is not None:
        job_repo.mark_completed(job, existing_prediction.id)
        return

    result = _run_pipeline_for_job(helioviewer_date)
    prediction_payload = _build_prediction_payload(str(uuid4()), result)
    prediction = prediction_repo.save_prediction(prediction_payload)
    job_repo.mark_completed(job, prediction.id)


def process_one_job() -> bool:
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        prediction_repo = PredictionRepository(db)

        job = job_repo.get_next_queued_job()
        if job is None:
            return False

        logger.info("Claiming job %s", job.id)
        job_repo.mark_running(job)

        try:
            _process_claimed_job(job_repo, prediction_repo, job)
            logger.info("Job %s completed", job.id)
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job_repo.mark_failed(job, str(exc))

        return True
    finally:
        db.close()


def main() -> None:
    logger.info("Worker started")
    create_database_schema()

    while True:
        if not process_one_job():
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
