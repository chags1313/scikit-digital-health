"""
Unit tests for wear detection algorithms

Lukas Adamowicz
Pfizer DMTI 2021
"""
import pytest
import numpy as np

from skimu.preprocessing.wear_detection import DetectWear, _modify_wear_times


class TestWearDetection:
    @pytest.mark.parametrize(("setup", "ship"), ((False, [0, 0]), (True, [12, 12])))
    def test(self, setup, ship, accel_with_nonwear):
        dw = DetectWear(
            sd_crit=0.013,
            range_crit=0.05,
            apply_setup_criteria=setup,
            shipping_criteria=ship,
            window_length=60,
            window_skip=15,
        )

        time, accel, wear = accel_with_nonwear(setup, ship)

        res = dw.predict(time, accel)

        assert np.allclose(res["wear"], wear)

    @pytest.mark.parametrize(
        ("case", "setup", "ship"),
        (
            (1, False, [0, 0]),
            (1, True, [12, 12]),
            (2, False, [0, 0]),
            (2, True, [12, 12]),
            (3, False, [0, 0]),
            (3, True, [12, 12]),
            (4, False, [0, 0]),
            (4, True, [12, 12]),
        ),
    )
    def test_wear_time_modifiction(self, case, setup, ship, simple_nonwear_data):
        wskip = 15  # minutes

        nonwear, true_wear = simple_nonwear_data(case, wskip, setup, ship)

        starts, stops = _modify_wear_times(nonwear, wskip, setup, ship)

        assert np.allclose(starts, true_wear[:, 0])
        assert np.allclose(stops, true_wear[:, 1])
