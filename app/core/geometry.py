"""几何层：压下量与接触弧长（刚性辊，投影弧长）。

本版约定
--------
* 辊子为刚性，不做辊面弹性压扁（Hitchcock 轧辊压扁）修正。
* 接触弧长取其在轧制方向上的投影长度：

      Δh = H - h
      Lc = sqrt(R * Δh)

  其中
      Δh : 压下量 (mm)
      H  : 带材入口厚度 (mm)
      h  : 带材出口厚度 (mm)
      R  : 辊子半径 (mm)
      Lc : 接触弧长（投影长度, mm）

  因此 R 翻倍而 Δh 不变时，Lc 只按 sqrt(2) 增大，而非翻倍。

输入合法性（厚度、半径为正数等）统一在 :mod:`app.core.validation`
里处理，本模块只负责几何公式本身。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Geometry:
    """一道次的几何结果，长度单位均为 mm。"""

    entry_thickness: float
    """入口厚度 H (mm)"""

    exit_thickness: float
    """出口厚度 h (mm)"""

    roll_radius: float
    """辊子半径 R (mm)"""

    draft: float
    """压下量 Δh = H - h (mm)"""

    contact_length: float
    """接触弧长（投影长度） Lc = sqrt(R·Δh) (mm)"""

    mean_thickness: float
    """平均厚度 hm = (H + h) / 2 (mm)"""

    reduction_ratio: float
    """压下率 r = Δh / H，以小数表示（0.20 即 20%）"""


def compute_geometry(
    roll_radius: float,
    entry_thickness: float,
    exit_thickness: float,
) -> Geometry:
    """按刚性辊假设计算压下量与接触弧长。

    零压下（``entry_thickness == exit_thickness``）是合法工况：
    此时压下量、接触弧长均为 0，下游轧制力相应为 0。
    """
    draft = entry_thickness - exit_thickness
    contact_length = (roll_radius * draft) ** 0.5
    mean_thickness = (entry_thickness + exit_thickness) / 2.0
    reduction_ratio = draft / entry_thickness
    return Geometry(
        entry_thickness=entry_thickness,
        exit_thickness=exit_thickness,
        roll_radius=roll_radius,
        draft=draft,
        contact_length=contact_length,
        mean_thickness=mean_thickness,
        reduction_ratio=reduction_ratio,
    )
