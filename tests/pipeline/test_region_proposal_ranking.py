import numpy as np

from prediction.pipeline.stages.region_proposal import build_polygon_regions


def test_polygon_regions_are_ranked_by_normalized_area_weighted_score():
    score_map = np.zeros((64, 64), dtype=np.float32)
    score_map[2:13, 2:13] = 0.9
    score_map[20:51, 20:51] = 0.4

    small_hot_region = np.array([[2, 2], [12, 2], [12, 12], [2, 12]], dtype=np.int32)
    large_weaker_region = np.array([[20, 20], [50, 20], [50, 50], [20, 50]], dtype=np.int32)

    regions = build_polygon_regions(
        polygons=[large_weaker_region, small_hot_region],
        score_map=score_map,
    )

    assert regions[0]["polygon"] is small_hot_region
    assert regions[0]["ranking_score"] > regions[1]["ranking_score"]
    assert regions[0]["area_factor"] < regions[1]["area_factor"]
