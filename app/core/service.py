"""最薄编排层：校验 -> 几何 -> 平均压力 -> 轧制力与力矩。

这里的 :func:`calculate` 是纯函数：所有中间量（接触弧长、
平均压力等）都活在本次调用的局部对象里。并发的两组参数各自
得到独立的 :class:`PassResult`，一组的辊径不可能算进另一组。
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Geometry, compute_geometry
from .pressure import MeanPressure, compute_mean_pressure
from .rolling import DEFAULT_STRIP_WIDTH_MM, RollingResult, compute_rolling_force
from .validation import RollingInputs, validate_inputs


@dataclass(frozen=True)
class PassResult:
    """一个道次受力核算的完整结果，供接口层直接序列化。"""

    inputs: RollingInputs
    geometry: Geometry
    mean_pressure: MeanPressure
    rolling: RollingResult


def calculate(
    roll_radius: float,
    entry_thickness: float,
    exit_thickness: float,
    yield_stress: float,
    friction_factor: float,
    strip_width: float | None = None,
) -> PassResult:
    """跑一道次平板轧制受力核算。

    先做合法性校验（不合法直接抛 :class:`InvalidInputError`），
    再依次调用几何、压力、轧制力三块独立算子。
    """
    inputs: RollingInputs = validate_inputs(
        roll_radius=roll_radius,
        entry_thickness=entry_thickness,
        exit_thickness=exit_thickness,
        yield_stress=yield_stress,
        friction_factor=friction_factor,
        # 未给板宽时使用轧制力模块里的默认 1000 mm；
        # 显式给了 None 之外的值（含 0、负值）则照常进入校验。
        strip_width=strip_width if strip_width is not None else DEFAULT_STRIP_WIDTH_MM,
    )

    geom = compute_geometry(
        roll_radius=inputs.roll_radius,
        entry_thickness=inputs.entry_thickness,
        exit_thickness=inputs.exit_thickness,
    )
    mp = compute_mean_pressure(
        yield_stress=inputs.yield_stress,
        friction_factor=inputs.friction_factor,
        contact_length=geom.contact_length,
        mean_thickness=geom.mean_thickness,
    )
    rr = compute_rolling_force(
        mean_pressure=mp.mean_pressure,
        contact_length=geom.contact_length,
        strip_width=inputs.strip_width,
    )
    return PassResult(inputs=inputs, geometry=geom, mean_pressure=mp, rolling=rr)
