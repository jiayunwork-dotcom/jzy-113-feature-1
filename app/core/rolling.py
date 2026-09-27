"""由平均单位压力与接触面积合成总轧制力，再由力臂给出轧制力矩。

公式（原样列出）
----------------

接触面积（单根辊子与带材的接触面在轧制方向 × 板宽）::

    A = b * Lc

总轧制力（单辊，工程上也作为该道次的轧制力报出）::

    F = pm * A = pm * b * Lc

轧制力矩（单根工作辊），力臂取接触弧长的一半（合力作用点
取在接触弧中点的简化假设）::

    M = F * (Lc / 2)

符号约定::

    b  : 板（带）宽 (mm)，请求中可选，默认 1000 mm
    Lc : 接触弧长（投影长度） (mm)
    pm : 平均单位压力 (MPa = N/mm²)
    F  : 总轧制力 (N)
    M  : 轧制力矩 (N·mm)，对外换算为 kN·m

单位说明
--------
因为 1 MPa = 1 N/mm²，``pm (N/mm²) × b (mm) × Lc (mm)``
直接得到 N，不需要额外换算；力矩 1 N·mm = 1e-6 kN·m。

零压下时 Lc = 0，接触面积为 0，故 F = 0、M = 0。
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_STRIP_WIDTH_MM = 1000.0
"""默认板宽 (mm)：未指定板宽时按 1 m 宽带材报力。"""

LEVER_ARM_RATIO = 0.5
"""力臂系数：合力作用点取接触弧中点，力臂 a = 0.5·Lc。"""

N_PER_KN = 1.0e3
NMM_PER_KNM = 1.0e6


@dataclass(frozen=True)
class RollingResult:
    """轧制力与力矩合成结果。"""

    strip_width: float
    """板宽 b (mm)"""

    contact_area: float
    """接触面积 A = b·Lc (mm²)"""

    rolling_force_n: float
    """总轧制力 F (N)"""

    rolling_force_mn: float
    """总轧制力 F (MN)，便于核对量级"""

    lever_arm: float
    """力臂 a = 0.5·Lc (mm)"""

    rolling_torque_nm: float
    """轧制力矩 M (N·m，单辊)"""

    rolling_torque_knm: float
    """轧制力矩 M (kN·m，单辊)"""


def compute_rolling_force(
    mean_pressure: float,
    contact_length: float,
    strip_width: float = DEFAULT_STRIP_WIDTH_MM,
) -> RollingResult:
    """合成总轧制力与单辊轧制力矩。

    参数
    ----
    mean_pressure:
        平均单位压力 pm (MPa)。
    contact_length:
        接触弧长 Lc (mm)。
    strip_width:
        板宽 b (mm)，默认 1000 mm。
    """
    area = strip_width * contact_length
    force_n = mean_pressure * area
    lever_arm = LEVER_ARM_RATIO * contact_length
    torque_nmm = force_n * lever_arm
    return RollingResult(
        strip_width=strip_width,
        contact_area=area,
        rolling_force_n=force_n,
        rolling_force_mn=force_n / 1.0e6,
        lever_arm=lever_arm,
        rolling_torque_nm=torque_nmm / 1.0e3,
        rolling_torque_knm=torque_nmm / NMM_PER_KNM,
    )
