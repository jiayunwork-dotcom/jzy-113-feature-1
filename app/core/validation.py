"""入参合法性校验：在开方、除法发生之前拦下不合规输入。

任何不合规输入都抛出 :class:`InvalidInputError`，携带字段名与
中文原因，由最外层接口统一转成带原因的错误响应，而不是让
``sqrt`` 或除法在中途抛出含义不清的异常。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .rolling import DEFAULT_STRIP_WIDTH_MM


class InvalidInputError(ValueError):
    """输入不满足物理约束。``field`` 为出错字段，``reason`` 为中文原因。"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


# 各数值字段的中文名，便于错误响应直接说人话。
_FIELD_LABELS = {
    "roll_radius": "辊子半径",
    "entry_thickness": "入口厚度",
    "exit_thickness": "出口厚度",
    "yield_stress": "屈服应力",
    "friction_factor": "摩擦因子",
    "strip_width": "板宽",
}


@dataclass(frozen=True)
class RollingInputs:
    """通过校验后的一道次原始输入（单位见各字段说明）。"""

    roll_radius: float
    """辊子半径 R (mm)，必须为正数"""
    entry_thickness: float
    """入口厚度 H (mm)，必须为正数"""
    exit_thickness: float
    """出口厚度 h (mm)，必须 > 0 且 <= 入口厚度"""
    yield_stress: float
    """材料屈服应力 sigma_s (MPa)，必须为正数"""
    friction_factor: float
    """摩擦因子 mu（无量纲），必须 >= 0"""
    strip_width: float = DEFAULT_STRIP_WIDTH_MM
    """板宽 b (mm)，必须为正数；缺省 1000 mm"""


def _check_finite(field: str, value: object) -> float:
    """要求字段是有限数值（拒绝 None、字符串、NaN、Inf）。"""
    label = _FIELD_LABELS[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(field, f"{label}必须是数值，收到的是 {value!r}")
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise InvalidInputError(field, f"{label}必须是有限数值，收到的是 {value!r}")
    return fvalue


def validate_inputs(
    roll_radius: object,
    entry_thickness: object,
    exit_thickness: object,
    yield_stress: object,
    friction_factor: object,
    strip_width: object = DEFAULT_STRIP_WIDTH_MM,
) -> RollingInputs:
    """按物理约束逐个校验入参，全部通过后返回冻结的 :class:`RollingInputs`。

    校验顺序：先有限数值，再取值范围，最后厚度关系。
    """
    radius = _check_finite("roll_radius", roll_radius)
    entry = _check_finite("entry_thickness", entry_thickness)
    exit_t = _check_finite("exit_thickness", exit_thickness)
    ys = _check_finite("yield_stress", yield_stress)
    mu = _check_finite("friction_factor", friction_factor)
    width = _check_finite("strip_width", strip_width)

    if radius <= 0:
        raise InvalidInputError("roll_radius", f"辊子半径必须是正数，收到 {radius}")
    if entry <= 0:
        raise InvalidInputError("entry_thickness", f"入口厚度必须是正数，收到 {entry}")
    if exit_t <= 0:
        raise InvalidInputError("exit_thickness", f"出口厚度必须大于零，收到 {exit_t}")
    if exit_t > entry:
        raise InvalidInputError(
            "exit_thickness",
            f"出口厚度({exit_t})不能大于入口厚度({entry})，平板轧制只压下不增厚",
        )
    if ys <= 0:
        raise InvalidInputError("yield_stress", f"屈服应力必须是正数，收到 {ys}")
    if mu < 0:
        raise InvalidInputError("friction_factor", f"摩擦因子不能为负值，收到 {mu}")
    if width <= 0:
        raise InvalidInputError("strip_width", f"板宽必须是正数，收到 {width}")

    return RollingInputs(
        roll_radius=radius,
        entry_thickness=entry,
        exit_thickness=exit_t,
        yield_stress=ys,
        friction_factor=mu,
        strip_width=width,
    )
