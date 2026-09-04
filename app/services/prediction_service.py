from datetime import datetime

from app.api.repositories.prediction_repository import PredictionRepository
from app.api.schemas.prediction import (
    ActiveRegionResponse,
    HeatmapResponse,
    PredictionHistoryPage,
    PredictionResponse,
)
from app.models.prediction import PredictionRecord


class PredictionService:
    def __init__(self, repo: PredictionRepository):
        self.repo = repo

    def list_prediction_history(
        self,
        *,
        page: int,
        page_size: int,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        predicted_class: int | None = None,
    ) -> PredictionHistoryPage:
        records, total = self.repo.list_predictions_page(
            page=page,
            page_size=page_size,
            start_at=start_at,
            end_at=end_at,
            predicted_class=predicted_class,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return PredictionHistoryPage(
            items=[self._to_response(record) for record in records],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def get_latest_prediction(self) -> PredictionResponse:
        record = self.repo.get_latest_prediction()
        if record is None:
            raise ValueError("No prediction found")
        return self._to_response(record)

    def _to_response(self, record: PredictionRecord) -> PredictionResponse:
        heatmaps_by_method = {
            heatmap.get("method_name"): heatmap.get("image_path")
            for heatmap in record.heatmaps
        }
        consensus = heatmaps_by_method.get("Consensus")
        legacy_heatmap = next(
            (
                heatmap.get("image_path")
                for heatmap in record.heatmaps
                if heatmap.get("method_name") in {"Heatmap", "Proposal Heatmap"}
                or "heatmap" in heatmap.get("image_path", "")
                or "proposal_heatmap" in heatmap.get("image_path", "")
            ),
            None,
        )
        final_hulls = next(
            (
                heatmap.get("image_path")
                for heatmap in record.heatmaps
                if heatmap.get("method_name") == "Final Region Hulls"
                or heatmap.get("method_name") == "Buffered Solar Mask"
                or "final_hulls" in heatmap.get("image_path", "")
                or "buffered_mask" in heatmap.get("image_path", "")
            ),
            None,
        )
        return PredictionResponse(
            prediction_id=record.id,
            requested_at=record.requested_at.isoformat(),
            timestamp=record.created_at.isoformat(),
            global_flare_probability=record.global_flare_probability,
            localized_probabilities=record.localized_probabilities,
            predicted_class="flare" if record.predicted_class == 1 else "non-flare",
            jp2_image_url=record.jp2_object_path,
            full_disk_image_url=record.full_disk_image_path,
            heatmap_url=consensus or legacy_heatmap,
            guided_gradcam_url=heatmaps_by_method.get("Guided Grad-CAM"),
            integrated_gradients_url=heatmaps_by_method.get("Integrated Gradients"),
            deepshap_url=heatmaps_by_method.get("DeepLiftShap"),
            consensus_url=consensus,
            final_hulls_url=final_hulls,
            active_regions=[
                ActiveRegionResponse(
                    rank=region["rank"],
                    probability=region["probability"],
                    heatmap_score=region.get("heatmap_score"),
                    image_path=region.get("image_path"),
                    bbox_original=region.get("bbox_original"),
                    bbox_resized=region.get("bbox_resized"),
                    center_original=region.get("center_original"),
                    center_resized=region.get("center_resized"),
                    polygon_original=region.get("polygon_original", []),
                    polygon_resized=region.get("polygon_resized", []),
                    crop_box_original=region.get("crop_box_original"),
                    crop_box_clipped_original=region.get("crop_box_clipped_original"),
                    crop_padding_ltrb=region.get("crop_padding_ltrb"),
                    proposal_score=region.get("proposal_score"),
                    consensus_score=region.get("consensus_score"),
                    area_weighted_score=region.get("area_weighted_score"),
                    area_resized=region.get("area_resized"),
                )
                for region in record.active_regions
            ],
            heatmaps=[
                HeatmapResponse(
                    method_name=heatmap["method_name"],
                    image_path=heatmap["image_path"],
                )
                for heatmap in record.heatmaps
            ],
            raw_active_regions=record.active_regions,
        )
