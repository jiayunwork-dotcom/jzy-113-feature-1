"""命名参数组存取，以及“两组参数各算各的、中间量互不串台”。"""

from __future__ import annotations

import threading

import pytest

from app.core.parameters import (
    ParameterNotFoundError,
    ParameterStore,
)
from app.core.service import calculate
from app.core.validation import InvalidInputError

VALID = dict(
    roll_radius=200.0,
    entry_thickness=2.0,
    exit_thickness=1.8,
    yield_stress=300.0,
    friction_factor=0.1,
    strip_width=1000.0,
)


def test_put_get_roundtrip() -> None:
    store = ParameterStore()
    store.put("Q235-2mm", **VALID)
    ps = store.get("Q235-2mm")
    assert ps.inputs.roll_radius == 200.0
    assert ps.inputs.yield_stress == 300.0


def test_get_missing_raises_named_error() -> None:
    store = ParameterStore()
    with pytest.raises(ParameterNotFoundError) as exc_info:
        store.get("no-such-set")
    assert exc_info.value.name == "no-such-set"


def test_delete_and_list() -> None:
    store = ParameterStore()
    store.put("a", **VALID)
    store.put("b", **{**VALID, "yield_stress": 500.0})
    assert {p.name for p in store.list_all()} == {"a", "b"}
    store.delete("a")
    assert {p.name for p in store.list_all()} == {"b"}
    with pytest.raises(ParameterNotFoundError):
        store.delete("a")


def test_put_validates_before_saving() -> None:
    store = ParameterStore()
    with pytest.raises(InvalidInputError):
        store.put("bad", **{**VALID, "roll_radius": -1.0})
    with pytest.raises(ParameterNotFoundError):
        store.get("bad")  # 不合规参数没有落库


def test_blank_name_rejected() -> None:
    store = ParameterStore()
    with pytest.raises(InvalidInputError):
        store.put("   ", **VALID)


def test_two_sets_never_cross_contaminate() -> None:
    """核心隔离：一组的辊径绝不能算到另一组结果里。

    两组除辊径外完全相同，各自反复计算，结果必须严格只由本组参数决定。
    """
    small = calculate(**{**VALID, "roll_radius": 200.0})
    big = calculate(**{**VALID, "roll_radius": 400.0})

    # 交错多次调用，模拟两组请求并发穿插
    results_small = []
    results_big = []
    for _ in range(5):
        results_small.append(calculate(**{**VALID, "roll_radius": 200.0}))
        results_big.append(calculate(**{**VALID, "roll_radius": 400.0}))

    for r in results_small:
        assert r.inputs.roll_radius == 200.0
        assert r.geometry.contact_length == small.geometry.contact_length
        assert r.rolling.rolling_force_n == small.rolling.rolling_force_n
    for r in results_big:
        assert r.inputs.roll_radius == 400.0
        assert r.geometry.contact_length == big.geometry.contact_length
        assert r.rolling.rolling_force_n == big.rolling.rolling_force_n

    # 比值只由 sqrt(2) 的弧长差异引起，与调用顺序无关
    ratio = big.geometry.contact_length / small.geometry.contact_length
    assert ratio == pytest.approx(2.0**0.5)


def test_concurrent_calculations_are_independent() -> None:
    """多线程并发各算各的参数，结果与串行一致。"""
    serial = {
        r: calculate(**{**VALID, "roll_radius": float(r)}).rolling.rolling_force_n
        for r in range(100, 200, 10)
    }
    collected: dict[float, float] = {}
    lock = threading.Lock()

    def worker(radius: float) -> None:
        res = calculate(**{**VALID, "roll_radius": radius})
        with lock:
            collected[radius] = res.rolling.rolling_force_n

    threads = [
        threading.Thread(target=worker, args=(float(r),))
        for r in range(100, 200, 10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert collected == serial
