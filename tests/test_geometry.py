"""几何层公式测试：专门盯 Lc = sqrt(R·Δh) 有没有写对。"""

from __future__ import annotations

import math

import pytest

from app.core.geometry import compute_geometry


def test_zero_draft_gives_zero_contact_length() -> None:
    """出口厚度等于入口厚度 = 没压下：压下量与弧长都为 0。"""
    g = compute_geometry(roll_radius=200.0, entry_thickness=2.0, exit_thickness=2.0)
    assert g.draft == 0.0
    assert g.contact_length == 0.0
    assert g.reduction_ratio == 0.0


def test_contact_length_is_sqrt_of_radius_times_draft() -> None:
    """Lc = sqrt(R·Δh) 的直接数值核对。"""
    g = compute_geometry(roll_radius=200.0, entry_thickness=2.0, exit_thickness=1.8)
    assert g.draft == pytest.approx(0.2)
    assert g.contact_length == pytest.approx(math.sqrt(200.0 * 0.2))
    assert g.mean_thickness == pytest.approx(1.9)
    assert g.reduction_ratio == pytest.approx(0.1)


def test_doubling_radius_scales_contact_length_by_sqrt_two() -> None:
    """验收铁律：其它不变、半径翻倍，弧长只按 sqrt(2) 变大，不翻倍。

    谁要是把弧长写成 R·Δh 忘了开根号，这条立刻露馅。
    """
    base = compute_geometry(200.0, 2.0, 1.8)
    doubled = compute_geometry(400.0, 2.0, 1.8)
    assert doubled.contact_length == pytest.approx(base.contact_length * math.sqrt(2.0))
    # 显式断言它没有翻倍
    assert doubled.contact_length != pytest.approx(base.contact_length * 2.0)
    assert doubled.contact_length < base.contact_length * 2.0


def test_larger_draft_lengthens_contact_arc() -> None:
    """压下量加大（出口更薄），接触弧长必须跟着涨。"""
    small = compute_geometry(200.0, 2.0, 1.9)
    medium = compute_geometry(200.0, 2.0, 1.8)
    large = compute_geometry(200.0, 2.0, 1.6)
    assert small.contact_length < medium.contact_length < large.contact_length
    assert small.draft < medium.draft < large.draft
