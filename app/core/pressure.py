"""平均单位压力公式。

采用“屈服应力 × 增强因子”的摩擦峰近似（常称简化摩擦峰模型，
Bland-Ford / Sims 一族公式的工程简化版），**不做辊面弹性压扁修正**。

公式（原样列出）
----------------

平面应变约束屈服应力::

    k = 1.15 * sigma_s

增强因子（受压下区摩擦峰抬高平均单位压力）::

    Q = 1 + mu * Lc / hm

平均单位压力::

    pm = k * Q
       = 1.15 * sigma_s * (1 + mu * Lc / hm)

符号约定（长度单位只要彼此一致即可，本服务统一用 mm）::

    sigma_s : 材料屈服应力 (MPa = N/mm²)
    k       : 平面应变约束屈服应力 (MPa)
    mu      : 辊面与带材之间的摩擦因子（库仑摩擦系数，无量纲）
    Lc      : 接触弧长（投影长度） (mm)，见 app.core.geometry
    hm      : 带材平均厚度 hm = (H + h) / 2 (mm)
    Q       : 摩擦/几何增强因子（无量纲）
    pm      : 平均单位压力 (MPa = N/mm²)

单调性（验收关系的依据）
------------------------
* ``mu`` 单独增大时 Q 增大，故 pm 增大；
* 压下量 Δh 增大（出口更薄）时 Lc 增大、hm 减小，
  Lc / hm 增大，故 pm 增大；
* 零压下时 Lc = 0，Q = 1，但此时接触面积为 0，
  轧制力仍为 0（见 app.core.rolling）。
"""

from __future__ import annotations

from dataclasses import dataclass

PLANE_STRAIN_FACTOR = 1.15
"""平面应变约束系数 2/sqrt(3) ≈ 1.15。"""


@dataclass(frozen=True)
class MeanPressure:
    """平均单位压力相关结果。"""

    yield_stress: float
    """材料屈服应力 sigma_s (MPa)"""

    constrained_yield_stress: float
    """平面应变约束屈服应力 k = 1.15·sigma_s (MPa)"""

    friction_factor: float
    """摩擦因子 mu（无量纲）"""

    contact_length: float
    """接触弧长 Lc (mm)"""

    mean_thickness: float
    """平均厚度 hm (mm)"""

    enhancement: float
    """增强因子 Q = 1 + mu·Lc/hm（无量纲）"""

    mean_pressure: float
    """平均单位压力 pm = k·Q (MPa)"""


def compute_mean_pressure(
    yield_stress: float,
    friction_factor: float,
    contact_length: float,
    mean_thickness: float,
) -> MeanPressure:
    """按简化摩擦峰公式计算平均单位压力。

    零压下时 ``contact_length == 0``，增强因子退化为 1。
    ``mean_thickness`` 恒为正（入口、出口厚度均已在合法性校验中
    要求为正），因此这里不存在除零风险。
    """
    constrained = PLANE_STRAIN_FACTOR * yield_stress
    enhancement = 1.0 + friction_factor * contact_length / mean_thickness
    pm = constrained * enhancement
    return MeanPressure(
        yield_stress=yield_stress,
        constrained_yield_stress=constrained,
        friction_factor=friction_factor,
        contact_length=contact_length,
        mean_thickness=mean_thickness,
        enhancement=enhancement,
        mean_pressure=pm,
    )
