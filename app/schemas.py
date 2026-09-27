"""HTTP 层的请求/响应数据模型（Pydantic v2）。

数值字段刻意不声明成 ``float`` 强转类型，而是 ``object`` 进来后
交给 :mod:`app.core.validation`，保证类型不对、NaN/Inf 等也能
返回统一的“带字段、带原因”错误响应。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.core.geometry import Geometry
from app.core.parameters import ParameterSet
from app.core.pressure import MeanPressure
from app.core.rolling import RollingResult
from app.core.service import PassResult
from app.core.validation import RollingInputs


class CalculateRequest(BaseModel):
    """一道次受力核算请求；长度单位 mm，应力单位 MPa。"""

    model_config = ConfigDict(extra="forbid")

    roll_radius: Any = ...
    """辊子半径 R (mm)，必须为正数"""
    entry_thickness: Any = ...
    """入口厚度 H (mm)，必须为正数"""
    exit_thickness: Any = ...
    """出口厚度 h (mm)，必须 > 0 且 <= H；h == H 为零压下"""
    yield_stress: Any = ...
    """材料屈服应力 sigma_s (MPa)，必须为正数"""
    friction_factor: Any = ...
    """摩擦因子 mu（无量纲），必须 >= 0"""
    strip_width: Optional[Any] = None
    """板宽 b (mm)，可选，缺省 1000 mm（按 1 m 宽带材报力）"""


class GeometryOut(BaseModel):
    draft_mm: float
    contact_length_mm: float
    mean_thickness_mm: float
    reduction_ratio: float
    reduction_percent: float


class MeanPressureOut(BaseModel):
    constrained_yield_stress_mpa: float
    enhancement_factor: float
    mean_pressure_mpa: float


class RollingOut(BaseModel):
    strip_width_mm: float
    contact_area_mm2: float
    rolling_force_n: float
    rolling_force_mn: float
    lever_arm_mm: float
    rolling_torque_nm: float
    rolling_torque_knm: float


class CalculateResponse(BaseModel):
    inputs: dict[str, Any]
    geometry: GeometryOut
    mean_pressure: MeanPressureOut
    rolling: RollingOut


class ErrorResponse(BaseModel):
    """统一错误响应：错误类型 + 出错字段 + 中文原因。"""

    error: str
    field: Optional[str] = None
    reason: str


class ParameterSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roll_radius: Any = ...
    entry_thickness: Any = ...
    exit_thickness: Any = ...
    yield_stress: Any = ...
    friction_factor: Any = ...
    strip_width: Optional[Any] = None


class ParameterSetOut(BaseModel):
    name: str
    inputs: dict[str, Any]


def _inputs_dict(inputs: RollingInputs) -> dict[str, Any]:
    return {
        "roll_radius_mm": inputs.roll_radius,
        "entry_thickness_mm": inputs.entry_thickness,
        "exit_thickness_mm": inputs.exit_thickness,
        "yield_stress_mpa": inputs.yield_stress,
        "friction_factor": inputs.friction_factor,
        "strip_width_mm": inputs.strip_width,
    }


def build_calculate_response(result: PassResult) -> CalculateResponse:
    geom: Geometry = result.geometry
    mp: MeanPressure = result.mean_pressure
    rr: RollingResult = result.rolling
    return CalculateResponse(
        inputs=_inputs_dict(result.inputs),
        geometry=GeometryOut(
            draft_mm=geom.draft,
            contact_length_mm=geom.contact_length,
            mean_thickness_mm=geom.mean_thickness,
            reduction_ratio=geom.reduction_ratio,
            reduction_percent=geom.reduction_ratio * 100.0,
        ),
        mean_pressure=MeanPressureOut(
            constrained_yield_stress_mpa=mp.constrained_yield_stress,
            enhancement_factor=mp.enhancement,
            mean_pressure_mpa=mp.mean_pressure,
        ),
        rolling=RollingOut(
            strip_width_mm=rr.strip_width,
            contact_area_mm2=rr.contact_area,
            rolling_force_n=rr.rolling_force_n,
            rolling_force_mn=rr.rolling_force_mn,
            lever_arm_mm=rr.lever_arm,
            rolling_torque_nm=rr.rolling_torque_nm,
            rolling_torque_knm=rr.rolling_torque_knm,
        ),
    )


def build_parameter_set_out(ps: ParameterSet) -> ParameterSetOut:
    return ParameterSetOut(name=ps.name, inputs=_inputs_dict(ps.inputs))
