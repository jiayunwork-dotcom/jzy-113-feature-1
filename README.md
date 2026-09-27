# 平板轧制单道次受力核算服务

常年挂内网、随叫随算的 HTTP 计算服务：给它**辊子半径、带材入口厚度、出口厚度、材料屈服应力、摩擦因子**（板宽可选，默认 1 m），它返回这一道次的

* **接触弧长**（刚性辊投影弧长）
* **总轧制力**（同时报 N 和 MN，防量级看错）
* **轧制力矩**（单辊，报 N·m 和 kN·m）
* **压下率**（小数与百分比）

只做**平板（薄板）轧制单道次受力核算**这一件事。只有 HTTP/JSON 接口，不配网页，不含轧程排产、合同交货等车间管理功能。计算走明确的力学公式，**不是经验吨位查表**，也与球面赫兹接触的压强分布无关；本版按刚性辊处理，**不做辊面弹性压扁修正**。

---

## 1. 计算公式（原样列出）

长度单位统一用 **mm**，应力单位 **MPa（= N/mm²）**，因此
`N/mm² × mm × mm = N`，力的结果直接为牛，无需额外换算。

### 1.1 压下量与压下率

```
Δh = H - h
 r = Δh / H               （压下率；0.10 即 10%）
hm = (H + h) / 2          （平均厚度）
```

| 符号 | 含义 | 单位 |
| --- | --- | --- |
| H | 入口厚度 | mm |
| h | 出口厚度 | mm |
| Δh | 压下量 | mm |
| r | 压下率 | — |
| hm | 平均厚度 | mm |

零压下（h = H）合法：Δh = 0、Lc = 0、F = 0、M = 0。

### 1.2 接触弧长（刚性辊，投影长度）

```
Lc = √(R · Δh)
```

R 为辊子半径 (mm)，Lc 为接触弧在轧制方向上的投影长度 (mm)。

**关键比例**：其它条件不变、R 翻倍时，Lc 只按 **√2** 增大，而不是翻倍。
谁要是把弧长写成 `R·Δh` 忘了开根号，回归测试立刻露馅。

### 1.3 平均单位压力（简化摩擦峰模型）

采用“屈服应力 × 增强因子”的形式（Sims/Bland-Ford 一族的工程简化版），
公式与本仓库实现严格一致：

```
k  = 1.15 · σs                     （平面应变约束屈服应力，1.15 = 2/√3）
Q  = 1 + μ · Lc / hm               （摩擦/几何增强因子）
pm = k · Q
   = 1.15 · σs · (1 + μ · Lc / hm) （平均单位压力，MPa）
```

| 符号 | 含义 | 单位 |
| --- | --- | --- |
| σs | 材料屈服应力（单轴） | MPa |
| k | 平面应变约束屈服应力 | MPa |
| μ | 辊面与带材之间的摩擦因子（库仑摩擦系数） | — |
| Q | 增强因子 | — |
| pm | 平均单位压力 | MPa |

性质：μ 单独增大 → pm 增大；Δh 增大（出口更薄）→ Lc 增大、hm 减小 → Q 增大、pm 增大；
零压下时 Lc = 0、Q = 1，但接触面积为零，故轧制力仍为 0。

> 建模取舍（刻意说明，避免被当成“查表”或“赫兹接触”）：
> Q 取线性摩擦峰近似，覆盖 μ = 0 退化到约束屈服应力、随 μ 与 Lc/hm 单调上升等
> 基本物理关系，适用于工程级道次核算；未计入轧辊弹性压扁、张力、加工硬化与
> 屈服沿程变化。需要更高保真时，只需替换 `app/core/pressure.py` 一个文件，
> 几何与轧制力合成模块不受影响。

### 1.4 总轧制力

```
A = b · Lc                          （接触面积，mm²）
F = pm · A = pm · b · Lc            （总轧制力，N）
```

b 为板宽 (mm)，请求中可选，**默认 b = 1000 mm**（按 1 m 宽带材报力）。
响应同时给出 `rolling_force_n` 与 `rolling_force_mn`（÷10⁶），两者严格相差 10⁶。

### 1.5 轧制力矩

合力作用点取接触弧中点（力臂 a = Lc/2）：

```
a = 0.5 · Lc                        （力臂，mm）
M = F · a = F · 0.5 · Lc            （单辊轧制力矩，N·mm）
                                      对外报 N·m（÷10³）与 kN·m（÷10⁶）
```

---

## 2. 算例（已钉进回归测试）

R = 200 mm，H = 2.00 mm，h = 1.80 mm，σs = 300 MPa，μ = 0.10，b = 1000 mm：

```
Δh = 0.20 mm，r = 10%，hm = 1.90 mm
Lc = √(200×0.20) = √40 ≈ 6.3246 mm
k  = 345 MPa
Q  = 1 + 0.10×6.3246/1.90 ≈ 1.3329
pm ≈ 459.84 MPa
F  ≈ 459.84 × 1000 × 6.3246 ≈ 2.908 × 10⁶ N ≈ 2.91 MN
M  ≈ F × 3.1623 ≈ 9.20 kN·m（单辊）
```

力在**兆牛量级**（测试带 1～5 MN 护栏；若实现把结果写成两千多牛即失败）。

---

## 3. HTTP 接口

Base URL：`http://<host>:8000`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活检查 |
| POST | `/api/v1/roll/calculate` | 直接给参数算一道次 |
| PUT | `/api/v1/parameters/{name}` | 存（覆盖）一组命名参数，**存时即校验** |
| GET | `/api/v1/parameters` | 列出全部命名参数组 |
| GET | `/api/v1/parameters/{name}` | 取一组命名参数 |
| DELETE | `/api/v1/parameters/{name}` | 删除一组命名参数 |
| POST | `/api/v1/parameters/{name}/calculate` | 用已存参数组算一道次 |

### 3.1 计算请求 / 响应

请求体（长度 mm，应力 MPa；`strip_width` 可省略，默认 1000）：

```json
{
  "roll_radius": 200.0,
  "entry_thickness": 2.0,
  "exit_thickness": 1.8,
  "yield_stress": 300.0,
  "friction_factor": 0.1,
  "strip_width": 1000.0
}
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/roll/calculate \
  -H 'Content-Type: application/json' \
  -d '{"roll_radius":200,"entry_thickness":2.0,"exit_thickness":1.8,
       "yield_stress":300,"friction_factor":0.1}'
```

响应（节选）：

```json
{
  "inputs": { "roll_radius_mm": 200.0, "entry_thickness_mm": 2.0,
              "exit_thickness_mm": 1.8, "yield_stress_mpa": 300.0,
              "friction_factor": 0.1, "strip_width_mm": 1000.0 },
  "geometry": {
    "draft_mm": 0.2,
    "contact_length_mm": 6.324555320336758,
    "mean_thickness_mm": 1.9,
    "reduction_ratio": 0.1,
    "reduction_percent": 10.0
  },
  "mean_pressure": {
    "constrained_yield_stress_mpa": 345.0,
    "enhancement_factor": 1.3328713326493031,
    "mean_pressure_mpa": 459.84060976400957
  },
  "rolling": {
    "strip_width_mm": 1000.0,
    "contact_area_mm2": 6324.555320336758,
    "rolling_force_n": 2908287.374989866,
    "rolling_force_mn": 2.908287374989866,
    "lever_arm_mm": 3.162277660168379,
    "rolling_torque_nm": 9196.81219528019,
    "rolling_torque_knm": 9.19681219528019
  }
}
```

机器可读的接口 Schema：`GET /openapi.json`（HTML 文档页按“不配网页”要求已关闭）。

### 3.2 命名参数组

```bash
# 存
curl -X PUT http://127.0.0.1:8000/api/v1/parameters/Q235-2mm \
  -H 'Content-Type: application/json' \
  -d '{"roll_radius":200,"entry_thickness":2.0,"exit_thickness":1.8,
       "yield_stress":300,"friction_factor":0.1}'

# 用它算
curl -X POST http://127.0.0.1:8000/api/v1/parameters/Q235-2mm/calculate
```

参数组只存进程内存，**进程重启即丢失**（题目允许）。计算本身是纯函数：
两组参数并发计算时，接触弧、轧制力等中间量各归各的，一组的辊径不会算进另一组。

---

## 4. 输入校验与错误响应

所有校验发生在开方/除法**之前**。HTTP 层统一返回 422（找不到参数组为 404）：

```json
{ "error": "invalid_input", "field": "friction_factor",
  "reason": "摩擦因子不能为负值，收到 -0.1" }
```

规则：

| 字段 | 规则 |
| --- | --- |
| `roll_radius` | 必须为正数 |
| `entry_thickness` | 必须为正数 |
| `exit_thickness` | 必须 > 0，且 ≤ 入口厚度（相等 = 零压下，合法） |
| `yield_stress` | 必须为正数 |
| `friction_factor` | 必须 ≥ 0（= 0 合法，表示无摩擦假设） |
| `strip_width` | 给了就必须为正数；不给默认 1000 mm |

此外：非数值、`NaN`、`±Infinity`、布尔值、缺字段、多余字段一律 422，
同样带 `field` 与 `reason`，不会冒出 `math domain error` 或除零异常。

---

## 5. 运行

### Docker（一条命令）

```bash
docker build -t flat-rolling-force .
docker run --rm -p 8000:8000 flat-rolling-force
# 验证
curl http://127.0.0.1:8000/health
```

镜像自带 HEALTHCHECK 打 `/health`。

### 本地直接跑（Python 3.12）

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 测试

```bash
pip install -r requirements-dev.txt
pytest
```

---

## 6. 验收关系与对应测试

| 物理关系 | 测试 |
| --- | --- |
| 零压下轧制力必须为 0 | `tests/test_physics.py::test_zero_draft_force_is_zero`、`tests/test_api.py::test_zero_draft_http_force_zero` |
| 压下量加大 → 弧长、轧制力都涨 | `test_larger_draft_increases_force`、`test_larger_draft_lengthens_contact_arc` |
| 摩擦因子单独调大 → 轧制力上升 | `test_higher_friction_increases_force` |
| 半径翻倍 → 弧长按 √2（不是翻倍） | `test_doubling_radius_scales_contact_length_by_sqrt_two`、`test_radius_doubling_sqrt_two_through_http` |
| 算例钉死（F ≈ 2.91 MN，兆牛量级） | `tests/test_worked_example.py` |
| 非法输入带原因拦截 | `tests/test_validation.py`、`tests/test_api.py` |
| 两组参数互不串台 + 并发 | `tests/test_parameters.py` |

---

## 7. 代码结构（按职责摊开）

```
app/
  main.py                # 最外层接口：收请求、调算子、拼响应（不含公式）
  schemas.py             # HTTP 请求/响应模型与序列化
  core/
    geometry.py          # 几何：Δh、Lc=√(R·Δh)、hm、压下率
    pressure.py          # 平均单位压力公式：1.15·σs·(1+μ·Lc/hm)
    rolling.py           # 压力×面积→轧制力；力臂→力矩；默认板宽
    validation.py        # 输入合法性校验（InvalidInputError）
    parameters.py        # 命名参数组的进程内存取（带锁，易失）
    service.py           # 薄编排：校验→几何→压力→力/力矩（纯函数）
tests/                   # 纯函数级 + HTTP 端到端回归测试
Dockerfile               # python:3.12-slim，一条命令构建运行
```
