"""命名参数组的存取（进程内、易失）。

允许把常用的辊径 / 材料参数起个名字存起来反复调用；仅存于
进程内存，进程重启后全部丢失（题目明确允许）。

并发安全：FastAPI 的请求在线程池/事件循环里并发进入，存取
用一把锁保护底层字典。

“两组参数各算各的”不靠这里隔离：计算本身是纯函数
（:mod:`app.core.service` 每次调用持有自己的局部中间量），
本存储只负责按名字取回不可变的参数快照。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .validation import InvalidInputError, RollingInputs, validate_inputs


@dataclass(frozen=True)
class ParameterSet:
    """一组已命名、已通过校验的参数（保存时即校验，不可变）。"""

    name: str
    inputs: RollingInputs


class ParameterNotFoundError(KeyError):
    """按名字取不到参数组时抛出。"""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"参数组 {name!r} 不存在")


class ParameterStore:
    """线程安全的命名参数组内存存储。"""

    def __init__(self) -> None:
        self._items: dict[str, ParameterSet] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _check_name(name: object) -> str:
        if not isinstance(name, str) or not name.strip():
            raise InvalidInputError("name", "参数组名称必须是非空字符串")
        return name.strip()

    def put(
        self,
        name: str,
        roll_radius: float,
        entry_thickness: float,
        exit_thickness: float,
        yield_stress: float,
        friction_factor: float,
        strip_width: float,
    ) -> ParameterSet:
        """保存（或覆盖）一个命名参数组；保存前做完整合法性校验。"""
        clean_name = self._check_name(name)
        # 先校验再落库，避免不合规参数污染存储。
        inputs = validate_inputs(
            roll_radius=roll_radius,
            entry_thickness=entry_thickness,
            exit_thickness=exit_thickness,
            yield_stress=yield_stress,
            friction_factor=friction_factor,
            strip_width=strip_width,
        )
        ps = ParameterSet(name=clean_name, inputs=inputs)
        with self._lock:
            self._items[clean_name] = ps
        return ps

    def get(self, name: str) -> ParameterSet:
        clean_name = self._check_name(name)
        with self._lock:
            try:
                return self._items[clean_name]
            except KeyError:
                raise ParameterNotFoundError(clean_name) from None

    def delete(self, name: str) -> None:
        clean_name = self._check_name(name)
        with self._lock:
            if clean_name not in self._items:
                raise ParameterNotFoundError(clean_name)
            del self._items[clean_name]

    def list_all(self) -> list[ParameterSet]:
        with self._lock:
            return list(self._items.values())
