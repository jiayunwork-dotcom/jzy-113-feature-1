"""薄板压下算例回归测试。

算例（钉死，任何公式被误改都应在此暴露）
----------------------------------------
辊子半径 R = 200 mm（约 Φ400 工作辊）
入口厚度 H = 2.00 mm，出口厚度 h = 1.80 mm
压下量 Δh = 0.20 mm，压下率 10%
屈服应力 sigma_s = 300 MPa，摩擦因子 mu = 0.10
板宽 b = 1000 mm（默认 1 m 宽带材）

手算
----
Lc = sqrt(200 × 0.20) = sqrt(40) ≈ 6.3246 mm
hm = (2.00 + 1.80)/2 = 1.90 mm
k  = 1.15 × 300 = 345 MPa
Q  = 1 + 0.10 × 6.3246 / 1.90 ≈ 1.3329
pm = 345 × 1.3329 ≈ 459.84 MPa
A  = 1000 × 6.3246 = 6324.6 mm²
F  = 459.84 × 6324.6 ≈ 2.9083×10^6 N ≈ 2.91 MN
M  = F × 0.5 × Lc ≈ 2.9083e6 × 3.1623 ≈ 9.197e6 N·mm ≈ 9.20 kN·m

量级必须落在 **兆牛（MN）量级**：若有实现把结果写成两千多牛
（少算 1000 倍，把 MN 当 N），下面的量级断言会直接失败。
"""

from __future__ import annotations

import math

import pytest

from app.core.service import calculate

EXAMPLE = dict(
    roll_radius=200.0,
    entry_thickness=2.0,
    exit_thickness=1.8,
    yield_stress=300.0,
    friction_factor=0.1,
    strip_width=1000.0,
)


@pytest.fixture(scope="module")
def result():
    return calculate(**EXAMPLE)


def test_example_geometry(result) -> None:
    assert result.geometry.draft == pytest.approx(0.20)
    assert result.geometry.contact_length == pytest.approx(math.sqrt(40.0), rel=1e-9)
    assert result.geometry.mean_thickness == pytest.approx(1.90)
    assert result.geometry.reduction_ratio == pytest.approx(0.10)


def test_example_mean_pressure(result) -> None:
    assert result.mean_pressure.constrained_yield_stress == pytest.approx(345.0)
    assert result.mean_pressure.enhancement == pytest.approx(1.0 + 0.1 * math.sqrt(40.0) / 1.9)
    assert result.mean_pressure.mean_pressure == pytest.approx(459.840, rel=1e-4)


def test_example_force_regression_value(result) -> None:
    """钉死的回归值：F ≈ 2.908 MN。"""
    assert result.rolling.rolling_force_n == pytest.approx(2.90833e6, rel=1e-4)
    assert result.rolling.rolling_force_mn == pytest.approx(2.90833, rel=1e-4)


def test_example_force_is_meganewton_scale(result) -> None:
    """量级护栏：必须落在 1～5 MN。少算一个数量级即失败。"""
    f_mn = result.rolling.rolling_force_mn
    assert 1.0 < f_mn < 5.0
    # 同一结果的 N/MN 两种报法严格相差 1e6
    assert result.rolling.rolling_force_n == pytest.approx(
        result.rolling.rolling_force_mn * 1e6, rel=1e-12
    )


def test_example_torque(result) -> None:
    assert result.rolling.lever_arm == pytest.approx(0.5 * math.sqrt(40.0))
    assert result.rolling.rolling_torque_knm == pytest.approx(9.197, rel=1e-3)
    assert result.rolling.rolling_torque_nm == pytest.approx(9197.0, rel=1e-3)
