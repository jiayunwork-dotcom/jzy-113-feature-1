"""平均压力、轧制力、力矩的物理关系测试。"""

from __future__ import annotations

import pytest

from app.core.pressure import PLANE_STRAIN_FACTOR, compute_mean_pressure
from app.core.rolling import (
    LEVER_ARM_RATIO,
    compute_rolling_force,
)
from app.core.service import calculate

BASE = dict(
    roll_radius=200.0,
    entry_thickness=2.0,
    exit_thickness=1.8,
    yield_stress=300.0,
    friction_factor=0.1,
    strip_width=1000.0,
)


def test_zero_draft_force_is_zero() -> None:
    """验收第 1 条：出口厚度等于入口厚度，轧制力必须是 0（力矩也为 0）。"""
    r = calculate(
        roll_radius=200.0,
        entry_thickness=2.0,
        exit_thickness=2.0,
        yield_stress=300.0,
        friction_factor=0.1,
    )
    assert r.geometry.draft == 0.0
    assert r.geometry.contact_length == 0.0
    assert r.rolling.rolling_force_n == 0.0
    assert r.rolling.rolling_force_mn == 0.0
    assert r.rolling.rolling_torque_nm == 0.0
    assert r.rolling.contact_area == 0.0
    # 零压下时增强因子退化为 1，平均压力仍为约束屈服应力，只是接触面积为 0
    assert r.mean_pressure.enhancement == pytest.approx(1.0)
    assert r.mean_pressure.mean_pressure == pytest.approx(1.15 * 300.0)


def test_larger_draft_increases_force() -> None:
    """验收第 2 条：其它不动，压下量调大（出口更薄），弧长与轧制力都涨。"""
    light = calculate(**{**BASE, "exit_thickness": 1.9})
    medium = calculate(**{**BASE, "exit_thickness": 1.8})
    heavy = calculate(**{**BASE, "exit_thickness": 1.6})
    assert (
        light.geometry.contact_length
        < medium.geometry.contact_length
        < heavy.geometry.contact_length
    )
    assert (
        light.rolling.rolling_force_n
        < medium.rolling.rolling_force_n
        < heavy.rolling.rolling_force_n
    )


def test_higher_friction_increases_force() -> None:
    """验收第 3 条：单独把摩擦因子调大，轧制力应当上升。"""
    low = calculate(**{**BASE, "friction_factor": 0.05})
    mid = calculate(**{**BASE, "friction_factor": 0.15})
    high = calculate(**{**BASE, "friction_factor": 0.30})
    assert low.mean_pressure.enhancement < mid.mean_pressure.enhancement
    assert mid.mean_pressure.enhancement < high.mean_pressure.enhancement
    assert (
        low.rolling.rolling_force_n
        < mid.rolling.rolling_force_n
        < high.rolling.rolling_force_n
    )
    # 几何结果不受摩擦影响，严格相等
    assert low.geometry.contact_length == mid.geometry.contact_length


def test_radius_doubling_arc_sqrt_two_full_pipeline() -> None:
    """验收第 4 条：整链路半径翻倍，弧长按 sqrt(2)；力随面积等比例上浮。"""
    base = calculate(**BASE)
    doubled = calculate(**{**BASE, "roll_radius": 400.0})
    assert doubled.geometry.contact_length == pytest.approx(
        base.geometry.contact_length * (2.0**0.5)
    )


def test_mean_pressure_formula_matches_documentation() -> None:
    """pm = 1.15 * sigma_s * (1 + mu * Lc / hm)，与 README 原样一致。"""
    mp = compute_mean_pressure(
        yield_stress=300.0,
        friction_factor=0.1,
        contact_length=(200.0 * 0.2) ** 0.5,
        mean_thickness=1.9,
    )
    expected_q = 1.0 + 0.1 * (200.0 * 0.2) ** 0.5 / 1.9
    assert mp.constrained_yield_stress == pytest.approx(PLANE_STRAIN_FACTOR * 300.0)
    assert mp.enhancement == pytest.approx(expected_q)
    assert mp.mean_pressure == pytest.approx(PLANE_STRAIN_FACTOR * 300.0 * expected_q)


def test_force_equals_pressure_times_area_and_torque_uses_half_arc() -> None:
    """F = pm·b·Lc；M = F·0.5·Lc。两单位制（N/MN、N·m/kN·m）一致。"""
    r = calculate(**BASE)
    expected_force = (
        r.mean_pressure.mean_pressure * r.inputs.strip_width * r.geometry.contact_length
    )
    assert r.rolling.rolling_force_n == pytest.approx(expected_force)
    assert r.rolling.rolling_force_mn == pytest.approx(expected_force / 1.0e6)
    expected_torque_nm = expected_force * LEVER_ARM_RATIO * r.geometry.contact_length / 1000.0
    assert r.rolling.rolling_torque_nm == pytest.approx(expected_torque_nm)
    assert r.rolling.rolling_torque_knm == pytest.approx(expected_torque_nm / 1000.0)


def test_force_scales_linearly_with_strip_width() -> None:
    """板宽翻倍，轧制力翻倍（量级与单位核对的辅助关系）。"""
    one_m = calculate(**BASE)
    two_m = calculate(**{**BASE, "strip_width": 2000.0})
    assert two_m.rolling.rolling_force_n == pytest.approx(
        2.0 * one_m.rolling.rolling_force_n
    )


def test_force_module_zero_contact_zero_force() -> None:
    rr = compute_rolling_force(mean_pressure=400.0, contact_length=0.0, strip_width=1000.0)
    assert rr.rolling_force_n == 0.0
    assert rr.rolling_torque_nm == 0.0
