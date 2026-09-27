"""FastAPI 入口：只收请求、调下面的算子、把结果拼回去。

路由
----
GET  /health                       存活检查
POST /api/v1/roll/calculate        直接给参数算一道次
PUT  /api/v1/parameters/{name}     存（或覆盖）一组命名参数
GET  /api/v1/parameters            列出全部命名参数组
GET  /api/v1/parameters/{name}     取一组命名参数
DEL  /api/v1/parameters/{name}     删除一组命名参数
POST /api/v1/parameters/{name}/calculate   用已存参数组算一道次

服务范围只限平板轧制单道次受力核算；不配网页，不做排产/合同管理。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .core.parameters import ParameterNotFoundError, ParameterStore
from .core.rolling import DEFAULT_STRIP_WIDTH_MM
from .core.service import calculate
from .core.validation import InvalidInputError
from .schemas import (
    CalculateRequest,
    CalculateResponse,
    ParameterSetOut,
    ParameterSetRequest,
    build_calculate_response,
    build_parameter_set_out,
)

app = FastAPI(
    title="平板轧制单道次受力核算服务",
    description=(
        "输入辊子半径、入口/出口厚度、屈服应力、摩擦因子，"
        "返回接触弧长、总轧制力、轧制力矩与压下率。仅 HTTP API，无网页。"
    ),
    version="1.0.0",
    # 只经 HTTP 接口对外服务、不配网页：关掉自带的 HTML 文档页；
    # 保留机器可读的 openapi.json 供客户端/工具生成调用代码。
    docs_url=None,
    redoc_url=None,
)

# 命名参数组：进程内、易失，重启即清空。
_store = ParameterStore()


def _error_response(
    status_code: int, error: str, reason: str, field: str | None = None
) -> JSONResponse:
    body: dict[str, Any] = {"error": error, "reason": reason}
    if field is not None:
        body["field"] = field
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(InvalidInputError)
async def invalid_input_handler(_request: Request, exc: InvalidInputError) -> JSONResponse:
    """物理/数值约束不满足：开算之前拦下，带字段与中文原因。"""
    return _error_response(422, "invalid_input", exc.reason, exc.field)


@app.exception_handler(ParameterNotFoundError)
async def parameter_not_found_handler(
    _request: Request, exc: ParameterNotFoundError
) -> JSONResponse:
    return _error_response(404, "parameter_set_not_found", f"参数组 {exc.name!r} 不存在", "name")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """把请求体层面的错误（缺字段、多字段、JSON 非法）也统一成同一种错误结构。"""
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = [str(part) for part in first.get("loc", []) if part != "body"]
        field = ".".join(loc) if loc else None
        kind = first.get("type", "validation_error")
        if kind == "missing":
            reason = f"缺少必填字段 {field}"
        elif kind == "extra_forbidden":
            reason = f"出现了不被允许的字段 {field}"
        else:
            reason = first.get("msg", "请求体不合法")
    else:
        field, reason = None, "请求体不合法"
    return _error_response(422, "invalid_request", reason, field)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/roll/calculate", response_model=CalculateResponse)
def calculate_pass(req: CalculateRequest) -> CalculateResponse:
    result = calculate(
        roll_radius=req.roll_radius,
        entry_thickness=req.entry_thickness,
        exit_thickness=req.exit_thickness,
        yield_stress=req.yield_stress,
        friction_factor=req.friction_factor,
        strip_width=req.strip_width,
    )
    return build_calculate_response(result)


@app.put("/api/v1/parameters/{name}", response_model=ParameterSetOut)
def save_parameter_set(name: str, req: ParameterSetRequest) -> ParameterSetOut:
    ps = _store.put(
        name=name,
        roll_radius=req.roll_radius,
        entry_thickness=req.entry_thickness,
        exit_thickness=req.exit_thickness,
        yield_stress=req.yield_stress,
        friction_factor=req.friction_factor,
        strip_width=req.strip_width
        if req.strip_width is not None
        else DEFAULT_STRIP_WIDTH_MM,
    )
    return build_parameter_set_out(ps)


@app.get("/api/v1/parameters", response_model=list[ParameterSetOut])
def list_parameter_sets() -> list[ParameterSetOut]:
    return [build_parameter_set_out(ps) for ps in _store.list_all()]


@app.get("/api/v1/parameters/{name}", response_model=ParameterSetOut)
def get_parameter_set(name: str) -> ParameterSetOut:
    return build_parameter_set_out(_store.get(name))


@app.delete("/api/v1/parameters/{name}")
def delete_parameter_set(name: str) -> dict[str, str]:
    _store.delete(name)
    return {"status": "deleted", "name": name}


@app.post("/api/v1/parameters/{name}/calculate", response_model=CalculateResponse)
def calculate_with_saved_set(name: str) -> CalculateResponse:
    ps = _store.get(name)
    result = calculate(
        roll_radius=ps.inputs.roll_radius,
        entry_thickness=ps.inputs.entry_thickness,
        exit_thickness=ps.inputs.exit_thickness,
        yield_stress=ps.inputs.yield_stress,
        friction_factor=ps.inputs.friction_factor,
        strip_width=ps.inputs.strip_width,
    )
    return build_calculate_response(result)
