"""HTTP 接口端到端测试（FastAPI TestClient）。"""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_BODY = {
    "roll_radius": 200.0,
    "entry_thickness": 2.0,
    "exit_thickness": 1.8,
    "yield_stress": 300.0,
    "friction_factor": 0.1,
    "strip_width": 1000.0,
}


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_calculate_returns_all_outputs() -> None:
    resp = client.post("/api/v1/roll/calculate", json=VALID_BODY)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # 三类结果对外可查：接触弧长、轧制力、力矩
    assert body["geometry"]["contact_length_mm"] == pytest.approx(math.sqrt(40.0))
    assert body["geometry"]["draft_mm"] == pytest.approx(0.2)
    assert body["geometry"]["reduction_ratio"] == pytest.approx(0.1)
    assert body["geometry"]["reduction_percent"] == pytest.approx(10.0)
    assert body["rolling"]["rolling_force_mn"] == pytest.approx(2.90833, rel=1e-4)
    assert body["rolling"]["rolling_force_n"] == pytest.approx(2.90833e6, rel=1e-4)
    assert body["rolling"]["rolling_torque_knm"] == pytest.approx(9.197, rel=1e-3)


def test_calculate_defaults_strip_width_when_omitted() -> None:
    body = {k: v for k, v in VALID_BODY.items() if k != "strip_width"}
    resp = client.post("/api/v1/roll/calculate", json=body)
    assert resp.status_code == 200
    assert resp.json()["rolling"]["strip_width_mm"] == 1000.0


def test_zero_draft_http_force_zero() -> None:
    body = {**VALID_BODY, "exit_thickness": 2.0}
    resp = client.post("/api/v1/roll/calculate", json=body)
    assert resp.status_code == 200
    assert resp.json()["rolling"]["rolling_force_n"] == 0.0


@pytest.mark.parametrize(
    "overrides,field",
    [
        ({"exit_thickness": 0.0}, "exit_thickness"),
        ({"exit_thickness": -0.5}, "exit_thickness"),
        ({"exit_thickness": 2.5}, "exit_thickness"),
        ({"roll_radius": 0.0}, "roll_radius"),
        ({"roll_radius": -10.0}, "roll_radius"),
        ({"yield_stress": 0.0}, "yield_stress"),
        ({"friction_factor": -0.2}, "friction_factor"),
    ],
)
def test_invalid_input_http_422_with_reason(overrides, field) -> None:
    resp = client.post("/api/v1/roll/calculate", json={**VALID_BODY, **overrides})
    assert resp.status_code == 422
    err = resp.json()
    assert err["error"] == "invalid_input"
    assert err["field"] == field
    assert err["reason"]


def test_missing_field_http_422() -> None:
    body = {k: v for k, v in VALID_BODY.items() if k != "yield_stress"}
    resp = client.post("/api/v1/roll/calculate", json=body)
    assert resp.status_code == 422
    err = resp.json()
    assert err["field"] == "yield_stress"
    assert "缺少" in err["reason"]


def test_unknown_field_rejected() -> None:
    resp = client.post(
        "/api/v1/roll/calculate", json={**VALID_BODY, "scheduling_priority": 1}
    )
    assert resp.status_code == 422
    assert resp.json()["field"] == "scheduling_priority"


def test_nan_json_rejected_before_calculation() -> None:
    # httpx 自身拒绝编码 NaN，这里直接发带 NaN token 的原始报文：
    # Python 侧 json.loads 默认接受 NaN，随后由校验层拦截。
    raw = (
        '{"roll_radius": NaN, "entry_thickness": 2.0, "exit_thickness": 1.8,'
        ' "yield_stress": 300.0, "friction_factor": 0.1, "strip_width": 1000.0}'
    )
    resp = client.post(
        "/api/v1/roll/calculate",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["field"] == "roll_radius"
    assert resp.json()["reason"]


def test_named_parameter_set_lifecycle_and_calculate() -> None:
    name = "Q235-2mm-api"

    # 清理可能的残留
    client.delete(f"/api/v1/parameters/{name}")

    put = client.put(f"/api/v1/parameters/{name}", json=VALID_BODY)
    assert put.status_code == 200, put.text
    assert put.json()["name"] == name

    listed = client.get("/api/v1/parameters").json()
    assert any(p["name"] == name for p in listed)

    got = client.get(f"/api/v1/parameters/{name}")
    assert got.status_code == 200
    assert got.json()["inputs"]["roll_radius_mm"] == 200.0

    calc = client.post(f"/api/v1/parameters/{name}/calculate")
    assert calc.status_code == 200
    assert calc.json()["rolling"]["rolling_force_mn"] == pytest.approx(2.90833, rel=1e-4)

    deleted = client.delete(f"/api/v1/parameters/{name}")
    assert deleted.status_code == 200

    missing = client.get(f"/api/v1/parameters/{name}")
    assert missing.status_code == 404
    assert missing.json()["error"] == "parameter_set_not_found"

    calc_missing = client.post(f"/api/v1/parameters/{name}/calculate")
    assert calc_missing.status_code == 404


def test_invalid_parameters_not_saved() -> None:
    name = "bad-set-api"
    client.delete(f"/api/v1/parameters/{name}")
    resp = client.put(
        f"/api/v1/parameters/{name}", json={**VALID_BODY, "roll_radius": -5.0}
    )
    assert resp.status_code == 422
    assert client.get(f"/api/v1/parameters/{name}").status_code == 404


def test_radius_doubling_sqrt_two_through_http() -> None:
    """验收关系也能经接口单独构造输入核验：R 翻倍，Lc × sqrt(2)。"""
    r1 = client.post("/api/v1/roll/calculate", json=VALID_BODY).json()
    r2 = client.post(
        "/api/v1/roll/calculate", json={**VALID_BODY, "roll_radius": 400.0}
    ).json()
    lc1 = r1["geometry"]["contact_length_mm"]
    lc2 = r2["geometry"]["contact_length_mm"]
    assert lc2 / lc1 == pytest.approx(math.sqrt(2.0))
