"""输入合法性校验：开算之前拦下，全部带字段与中文原因。"""

from __future__ import annotations

import math

import pytest

from app.core.service import calculate
from app.core.validation import InvalidInputError, validate_inputs

BASE = dict(
    roll_radius=200.0,
    entry_thickness=2.0,
    exit_thickness=1.8,
    yield_stress=300.0,
    friction_factor=0.1,
)


@pytest.mark.parametrize(
    "field,overrides",
    [
        ("exit_thickness", {"exit_thickness": 0.0}),
        ("exit_thickness", {"exit_thickness": -1.0}),
        ("exit_thickness", {"exit_thickness": 2.5}),  # 出口比入口还厚
        ("roll_radius", {"roll_radius": 0.0}),
        ("roll_radius", {"roll_radius": -200.0}),
        ("entry_thickness", {"entry_thickness": 0.0}),
        ("entry_thickness", {"entry_thickness": -2.0}),
        ("yield_stress", {"yield_stress": 0.0}),
        ("yield_stress", {"yield_stress": -300.0}),
        ("friction_factor", {"friction_factor": -0.01}),
        ("strip_width", {"strip_width": 0.0}),
        ("strip_width", {"strip_width": -10.0}),
    ],
)
def test_invalid_scalars_rejected(field, overrides) -> None:
    params = {**BASE, **overrides}
    with pytest.raises(InvalidInputError) as exc_info:
        calculate(**params)
    assert exc_info.value.field == field
    assert exc_info.value.reason  # 非空中文原因


def test_zero_friction_factor_is_allowed() -> None:
    """摩擦因子为 0 是合法的（无摩擦轧制假设），增强因子退化为 1。"""
    r = calculate(200.0, 2.0, 1.8, 300.0, 0.0)
    assert r.mean_pressure.enhancement == pytest.approx(1.0)


def test_equal_thickness_is_valid_zero_draft() -> None:
    r = calculate(200.0, 2.0, 2.0, 300.0, 0.1)
    assert r.rolling.rolling_force_n == 0.0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_rejected(bad) -> None:
    with pytest.raises(InvalidInputError) as exc_info:
        calculate(bad, 2.0, 1.8, 300.0, 0.1)
    assert exc_info.value.field == "roll_radius"


@pytest.mark.parametrize("bad", [None, "200", True, False, [200.0]])
def test_wrong_types_rejected(bad) -> None:
    with pytest.raises(InvalidInputError) as exc_info:
        validate_inputs(bad, 2.0, 1.8, 300.0, 0.1)
    assert exc_info.value.field == "roll_radius"


def test_validation_runs_before_any_sqrt_or_division() -> None:
    """出口厚于入口必须在 sqrt 之前被拦下，而不是冒出 math domain error。"""
    with pytest.raises(InvalidInputError) as exc_info:
        calculate(200.0, 2.0, 3.0, 300.0, 0.1)
    assert exc_info.value.field == "exit_thickness"


def test_default_strip_width_when_omitted() -> None:
    r = calculate(200.0, 2.0, 1.8, 300.0, 0.1)
    assert r.inputs.strip_width == 1000.0


def test_nan_yield_stress_is_rejected_with_field_name() -> None:
    with pytest.raises(InvalidInputError) as exc_info:
        calculate(200.0, 2.0, 1.8, math.nan, 0.1)
    assert exc_info.value.field == "yield_stress"
