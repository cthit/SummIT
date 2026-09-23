from datetime import date

import pytest

from project.data_handler import LP, infer_study_period_from_date


@pytest.mark.parametrize(
    "meeting_date, expected",
    [
        (date(2026, 9, 1), (2026, LP.LP1)),
        (date(2026, 10, 31), (2026, LP.LP1)),
        (date(2026, 11, 1), (2026, LP.LP2)),
        (date(2026, 12, 31), (2026, LP.LP2)),
        # Early January belongs to the previous year's LP2.
        (date(2027, 1, 15), (2026, LP.LP2)),
        (date(2027, 1, 16), (2027, LP.LP3)),
        (date(2027, 3, 31), (2027, LP.LP3)),
        (date(2027, 4, 1), (2027, LP.LP4)),
        (date(2027, 6, 15), (2027, LP.LP4)),
        (date(2027, 6, 16), (2027, LP.SUMMER)),
        (date(2027, 8, 31), (2027, LP.SUMMER)),
    ],
)
def test_infer_study_period_from_date(meeting_date, expected):
    assert infer_study_period_from_date(meeting_date) == expected
