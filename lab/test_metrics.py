"""Unit tests for the layer-2 metrics against shared-fixtures/metrics.json.

The fixtures file is the cross-language contract: the future TypeScript
implementation must pass the identical cases. Do not fix a failing test by
editing a fixture unless the spec itself changed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import metrics

FIXTURES = json.loads(
    (Path(__file__).parent.parent / "shared-fixtures" / "metrics.json").read_text()
)


def _to_args(raw: dict) -> dict:
    """JSON [x, y] arrays -> Point tuples; scalars pass through."""
    return {
        k: tuple(v) if isinstance(v, list) else v
        for k, v in raw.items()
    }


def _case_id(case: dict) -> str:
    return f"{case['function']}({case['inputs']})"


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=_case_id)
def test_fixture_case(case):
    fn = getattr(metrics, case["function"])
    result = fn(**_to_args(case["inputs"]))
    expected = case["expected"]

    if expected is None:  # null in JSON = NaN
        assert isinstance(result, float) and math.isnan(result)
    elif isinstance(expected, list):  # Point
        assert result == pytest.approx(tuple(expected), rel=1e-12)
    else:
        assert result == pytest.approx(expected, rel=1e-12)


def test_midpoint_is_symmetric():
    a, b = (12.3, 45.6), (-7.8, 9.0)
    assert metrics.midpoint(a, b) == metrics.midpoint(b, a)


def test_distance_is_symmetric():
    a, b = (12.3, 45.6), (-7.8, 9.0)
    assert metrics.distance(a, b) == metrics.distance(b, a)


def test_hip_height_uses_center_not_either_hip():
    # asymmetric hips: height must come from the midpoint
    left, right = (0.0, 100.0), (0.0, 300.0)
    assert metrics.hip_height(left, right, 1000.0) == 800.0
