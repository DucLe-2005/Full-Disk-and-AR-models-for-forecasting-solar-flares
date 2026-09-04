import numpy as np

from prediction.evaluation.localization import (
    active_region_hull_distances,
    collocation_ratio,
    convert_hgs_to_pixels,
    parse_event_position,
    proximity_score,
)


def test_parse_and_project_event_position():
    assert parse_event_position("S22E79( 4405 )") == {
        "ar_number": "AR4405",
        "longitude_deg": -79.0,
        "latitude_deg": -22.0,
    }
    assert convert_hgs_to_pixels(0, 0) == (256, 256)
    assert convert_hgs_to_pixels(-90, 0)[0] < 256
    assert convert_hgs_to_pixels(90, 0)[0] > 256


def test_hull_distances_and_collocation():
    hulls = [(1, np.array([[200, 200], [300, 200], [300, 300], [200, 300]]))]
    distances = active_region_hull_distances(
        [("AR1", (256, 256)), ("AR2", (100, 100))],
        hulls,
    )

    assert distances[0] == ("AR1", 1, 0.0, True)
    assert distances[1][1] == 1
    assert distances[1][2] > 0
    assert distances[1][3] is False
    assert collocation_ratio(distances) == 0.5
    assert proximity_score(distances) > 0
