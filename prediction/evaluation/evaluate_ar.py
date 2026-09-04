"""Evaluate active-region classifier predictions for attribution proposals."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import torch

from prediction.evaluation.localization import (
    active_regions_in_window,
    mark_actual_region_matches,
    prepare_2025_mx_event_regions,
    project_actual_regions,
    proposed_region_true_labels,
    save_localization_overlay,
)
from prediction.evaluation.metrics import accuracy, confusion_matrix, f1, precision, recall, tss, hss
from prediction.pipeline.stages.ar_predict import load_ar_model, predict_one_ar_image
from prediction.pipeline.stages.crop_regions import crop_proposed_active_regions_from_image
from prediction.pipeline.stages.region_proposal import PROPOSAL_IMAGE_SIZE, propose_active_regions


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMAGE_ROOT = REPOSITORY_ROOT / "data/2025"
EVENTS_PATH = REPOSITORY_ROOT / "data/events.csv"
OUTPUT_ROOT = REPOSITORY_ROOT / "data/active_region_evaluation_2025"
PREDICTIONS_PATH = OUTPUT_ROOT / "active_region_predictions.csv"
METRICS_PATH = OUTPUT_ROOT / "metrics.csv"
FINAL_HULLS_ROOT = OUTPUT_ROOT / "final_hulls_with_actual_ars"
AR_MODEL_NAME = "mobilenet"
THRESHOLD = 0.5


def _timestamp_from_image_path(image_path: Path) -> datetime.datetime:
    return datetime.datetime.strptime(
        image_path.stem.removeprefix("HMI.m"),
        "%Y.%m.%d_%H.%M.%S",
    )


def _jp2_path_for(image_path: Path) -> Path:
    jp2_path = image_path.parent.parent / "jp2" / f"{image_path.stem}.jp2"
    if not jp2_path.is_file():
        raise FileNotFoundError(f"Matching JP2 not found: {jp2_path}")
    return jp2_path


def main() -> None:
    if not EVENTS_PATH.is_file():
        raise FileNotFoundError(f"Event catalog not found: {EVENTS_PATH}")

    raw_events = pd.read_csv(EVENTS_PATH)
    events = prepare_2025_mx_event_regions(raw_events)
    image_paths = sorted(IMAGE_ROOT.glob("*/*/*/*/*/jpg/HMI.m*.jpg"))
    if not image_paths:
        raise FileNotFoundError(f"No 2025 HMI JPGs found under {IMAGE_ROOT}")

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model, checkpoint_path = load_ar_model(AR_MODEL_NAME, device=device)
    prediction_rows = []

    for image_path in image_paths:
        timestamp = _timestamp_from_image_path(image_path)
        print("Process AR predictions for", timestamp)
        actual_regions = active_regions_in_window(events, timestamp)
        proposal_result = propose_active_regions(image_path=image_path, save_artifacts=False)
        proposed_regions = proposal_result["regions"]
        actual_details = project_actual_regions(timestamp, actual_regions)
        true_labels = proposed_region_true_labels(proposed_regions, actual_details)

        crop_results = crop_proposed_active_regions_from_image(
            image_path=_jp2_path_for(image_path),
            regions=proposed_regions,
            output_dir=None,
            resize_to=PROPOSAL_IMAGE_SIZE,
        )
        for crop_result in crop_results:
            prediction = predict_one_ar_image(
                image=crop_result["image"],
                model=model,
                device=device,
                threshold=THRESHOLD,
            )
            region_rank = crop_result["region_rank"]
            prediction_rows.append(
                {
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "image_path": image_path.relative_to(REPOSITORY_ROOT).as_posix(),
                    "proposal_rank": region_rank,
                    "true_label": true_labels[region_rank],
                    "p_flare": prediction["ar_prob"],
                    "predicted_label": prediction["pred_class"],
                }
            )

        if not actual_details.empty:
            save_localization_overlay(
                image_path=str(image_path),
                proposed_regions=proposed_regions,
                details=mark_actual_region_matches(actual_details, proposed_regions),
                output_path=str(
                    FINAL_HULLS_ROOT
                    / f"{timestamp.strftime('%Y.%m.%d_%H.%M.%S')}_final_hulls_with_actual_ars.png"
                ),
            )
        print(
            f"{timestamp:%Y-%m-%d %H:%M:%S}: "
            f"proposals={len(proposed_regions)} actual_ars={len(actual_regions)}"
        )

    predictions = pd.DataFrame(
        prediction_rows,
        columns=[
            "timestamp",
            "image_path",
            "proposal_rank",
            "true_label",
            "p_flare",
            "predicted_label",
        ],
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    
    # TP: crop contains a cataloged M/X active region and MobileNet predicts flare.
    # TN: crop contains no cataloged M/X active region and MobileNet predicts non-flare.
    # FP: crop contains no cataloged M/X active region but MobileNet predicts flare.
    # FN: crop contains a cataloged M/X active region but MobileNet predicts non-flare. 
    matrix = confusion_matrix(predictions["true_label"], predictions["predicted_label"])
    summary = {
        **matrix,
        "accuracy": accuracy(matrix),
        "precision": precision(matrix),
        "recall": recall(matrix),
        "f1": f1(matrix),
        "tss": tss(matrix),
        "hss": hss(matrix)
    }
    pd.DataFrame([summary]).to_csv(METRICS_PATH, index=False)

    print(f"AR model: {AR_MODEL_NAME} ({checkpoint_path})")
    print(f"Proposed-region predictions: {PREDICTIONS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(pd.Series(summary))


if __name__ == "__main__":
    main()
