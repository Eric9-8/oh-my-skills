# Flash LiDAR Pattern 生成模板（1D 摆镜扫描）

**适用范围**：Hesai ATX/AT 系列、类似的半固态 LiDAR

---

## 核心概念

### aiSim 中 Flash LiDAR 的角度语义

对于 1D 摆镜扫描的 Flash LiDAR：
- **`AzimuthDeg`**：每条 ray 的**最终绝对方位角**（扫描角，不包含通道偏移）
- **扫描角**：需要由 pattern 显式给出（通常按 `TimeOffsetS`/step 线性覆盖水平 FOV）
- **`ElevationDeg`**：通道的固定俯仰角（来自手册附录）
- **`LaserId`**：推荐使用 `物理通道号 + (水平扫描序号 × 100)` 编码，便于调试和奇偶帧区分

### ⚠️ 关键理解：通道水平偏移量的处理

**Pattern 文件中包含通道水平偏移量**（基于 ATX100 实测）：

- ✅ **Pattern 包含**：扫描角度 + 通道水平偏移量
- ✅ **AzimuthDeg 语义**：每条 ray 的最终绝对方位角
- ✅ **计算公式**：`AzimuthDeg = scan_az(TimeOffsetS) + channel_azimuth_offset`

**手册中的"水平方位角偏移量"**（如 ±4.17°）：
- 来源：手册附录 A.1（通道分布数据）
- 用途：描述各通道的物理安装偏差
- 应用：**直接写入 Pattern 文件的 AzimuthDeg 字段**
- 验证：同一 TimeOffsetS 下，不同通道的 AzimuthDeg 应该不同（差异 = 通道偏移差）

**为什么 Pattern 包含偏移量？**
1. aiSim 的 `AzimuthDeg` 表示 ray 的绝对空间方向
2. 通道偏移是 LiDAR 的固有物理特性（不是校准误差）
3. Pattern 文件描述完整的扫描几何（包括通道分布）

### 与 Rotating LiDAR 的区别

| LiDAR 类型 | 角度字段 | 语义 |
|-----------|---------|------|
| **Rotating** | `AzimuthOffsetDeg` | 相对旋转轴的偏移 |
| **Flash (摆镜)** | `AzimuthDeg` | ray 的绝对方位角（理想扫描角） |

---

## 生成步骤

### 1. 提取通道数据（从手册附录）

手册通常在"通道分布"或附录中提供：

| 通道序号 | 偶数帧水平偏移 | 奇数帧水平偏移 | 垂直角度 |
|---------|--------------|--------------|---------|
| 1 | +4.17° | +4.17° | 6.98° |
| 2 | +3.81° | +3.81° | 6.58° |
| ... | ... | ... | ... |

**关键信息**：
- **偶数帧/奇数帧偏移**：✅ 这些偏移量**写入 Pattern 文件的 AzimuthDeg**
- **垂直角度**：✅ 写入 Pattern 的 `ElevationDeg` 字段
- **注意**：如果偶数帧和奇数帧偏移不同，需要生成两个周期（cycle）分别处理

### 2. 计算扫描参数

```python
# 基本参数（来自手册）
FRAME_RATE = 10  # Hz
H_FOV = 120      # degrees
H_RES = 0.1      # degrees

# 计算时间参数
FRAME_DURATION = 1.0 / FRAME_RATE  # 0.1 seconds
H_STEPS = int(H_FOV / H_RES)       # 1200 steps
TIME_PER_STEP = FRAME_DURATION / H_STEPS  # ~0.0000833 s

# 周期数（偶数帧 + 奇数帧）
MAX_STORED_CYCLES = 2
```

### 3. 生成 Pattern JSON（ATX100 实测逻辑）

```python
def generate_flash_lidar_pattern(channels, frame_rate, h_fov, h_res, cycles=2):
    """
    生成 Flash LiDAR 的 ScanningPattern（基于 ATX100 实测）

    Args:
        channels: [(manual_id, azimuth_offset, elevation), ...]  # ✅ 包含通道水平偏移量
        frame_rate: 帧率 (Hz)
        h_fov: 水平视场角 (degrees)
        h_res: 水平分辨率 (degrees)
        cycles: 周期数（默认 2：偶数帧+奇数帧）

    Returns:
        Pattern JSON 字典
    """
    frame_duration = 1.0 / frame_rate
    h_steps = int(h_fov / h_res)
    time_per_step = frame_duration / h_steps

    # 建立手册通道号到物理通道号的映射（手册从1开始，物理从0开始）
    channel_map = {}
    for manual_id, azimuth_offset, elevation in channels:
        physical_id = manual_id - 1  # 手册通道1 -> 物理通道0
        channel_map[physical_id] = (azimuth_offset, elevation)

    pattern = {"ScanningPattern": []}

    for cycle_idx in range(cycles):
        lasers = []

        for step in range(h_steps):
            # 计算当前时间偏移（跨周期递增）
            time_offset = cycle_idx * frame_duration + step * time_per_step

            # 计算基准扫描角（不含通道偏移）
            scan_az = -h_fov / 2 + step * h_res

            # 对于每个时间步，所有通道同时发射
            for physical_ch_id in sorted(channel_map.keys()):
                azimuth_offset, elevation = channel_map[physical_ch_id]

                # ✅ LaserId 编码：物理通道号 + (水平扫描序号 × 100)
                # 优点：
                # 1. 可读性：LaserId % 100 = 物理通道号
                # 2. 可追溯：LaserId // 100 = 水平扫描序号
                # 3. 奇偶帧区分：通过扫描序号区分
                laser_id = physical_ch_id + step * 100

                lasers.append({
                    "TimeOffsetS": time_offset,
                    "AzimuthDeg": scan_az + azimuth_offset,  # ✅ 扫描角 + 通道偏移
                    "ElevationDeg": elevation,
                    "LaserId": laser_id,
                    "MaxDistanceDegradation": 1.0  # 可选字段
                })

        # ✅ 按 LaserId 排序，确保输出有序（便于阅读和调试）
        lasers.sort(key=lambda x: x["LaserId"])
        pattern["ScanningPattern"].append({"Lasers": lasers})

    return pattern
```

### 4. JSON 格式优化（纵向展开）

```python
import json

def save_pattern_readable(pattern, output_path):
    """
    保存 Pattern JSON，使用纵向格式便于阅读
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pattern, f, indent=4, ensure_ascii=False)

    print(f"✅ Pattern 已保存到: {output_path}")
    print(f"   总点数: {len(pattern['ScanningPattern'][0]['Lasers'])}")
    print(f"   周期数: {len(pattern['ScanningPattern'])}")
```

### 5. 验证生成结果

```python
def validate_pattern(pattern, h_fov, num_channels):
    """
    验证生成的 Pattern 是否符合预期
    """
    lasers = pattern["ScanningPattern"][0]["Lasers"]

    # 检查方位角范围
    az_list = [l["AzimuthDeg"] for l in lasers]
    az_min, az_max = min(az_list), max(az_list)
    expected_min = -h_fov / 2
    expected_max = h_fov / 2 - 0.1  # 减去一个分辨率步长

    print(f"✅ 方位角范围: [{az_min:.2f}°, {az_max:.2f}°]")
    print(f"   预期范围: [{expected_min:.2f}°, {expected_max:.2f}°]")

    # 检查 LaserId 编码
    laser_ids = [l["LaserId"] for l in lasers]
    physical_channels = set([lid % 100 for lid in laser_ids])

    print(f"✅ 物理通道数: {len(physical_channels)} (预期 {num_channels})")
    print(f"   LaserId 范围: {min(laser_ids)} - {max(laser_ids)}")

    # 检查时间跨度
    time_offsets = [l["TimeOffsetS"] for l in lasers]
    time_span = max(time_offsets) - min(time_offsets)

    print(f"✅ 时间跨度: {time_span:.4f}s")

    return az_min, az_max, len(physical_channels)
```

---

## 常见错误与修正

### ❌ 错误 1：在 Pattern 中遗漏通道偏移量

```python
# ❌ 错误：仅使用扫描角，不包含通道偏移
for channel in channels:
    azimuth = scan_angle  # 错误！会导致所有通道方位角相同
```

**问题**：
- 同一 TimeOffsetS 下，所有通道的 AzimuthDeg 都相同
- 导出的点云会丢失通道间的水平分布差异
- 验证时会发现通道覆盖率异常

### ✅ 正确：使用扫描角 + 通道偏移

```python
# ✅ 正确：扫描角 + 通道偏移
for channel in channels:
    azimuth = scan_angle + channel.azimuth_offset  # 正确！
```

### ❌ 错误 2：LaserId 使用简单递增

```python
# ❌ 错误：简单递增，不便于调试
laser_id = 0
for step in range(h_steps):
    for channel in channels:
        lasers.append({"LaserId": laser_id, ...})
        laser_id += 1
```

**问题**：
- 无法从 LaserId 反推物理通道号
- 不便于调试和验证
- 无法区分奇偶帧

### ✅ 正确：使用编码方案 + 排序输出

```python
# ✅ 正确：LaserId = 物理通道号 + (扫描序号 × 100)
lasers = []
for step in range(h_steps):
    for physical_ch_id, channel in enumerate(channels):
        laser_id = physical_ch_id + step * 100
        lasers.append({
            "LaserId": laser_id,
            "AzimuthDeg": scan_az + channel.azimuth_offset,
            ...
        })

# ✅ 按 LaserId 排序，确保输出有序（便于阅读）
lasers.sort(key=lambda x: x["LaserId"])
```

**优点**：
- `LaserId % 100` = 物理通道号
- `LaserId // 100` = 水平扫描序号
- 输出有序，便于验证和调试

---

## 示例输出结构（基于 ATX100 实测）

```json
{
    "ScanningPattern": [
        {
            "Lasers": [
                {
                    "TimeOffsetS": 0.010172,
                    "AzimuthDeg": 59.4765625,
                    "ElevationDeg": 6.82421875,
                    "LaserId": 0,
                    "MaxDistanceDegradation": 1.0
                },
                {
                    "TimeOffsetS": 0.010172,
                    "AzimuthDeg": 59.07421875,
                    "ElevationDeg": 6.421875,
                    "LaserId": 1,
                    "MaxDistanceDegradation": 1.0
                },
                {
                    "TimeOffsetS": 0.010272,
                    "AzimuthDeg": 59.375,
                    "ElevationDeg": 6.82421875,
                    "LaserId": 100,
                    "MaxDistanceDegradation": 1.0
                }
            ]
        }
    ]
}
```

**关键观察**：
- ✅ `AzimuthDeg` 随 `TimeOffsetS` 变化（体现扫描角）
- ✅ 在同一 `TimeOffsetS` 下，不同通道的 `AzimuthDeg` **不同**（扫描角 + 通道偏移）
  - 例如：通道 0 和通道 1 在同一时刻的方位角差异 ≈ 0.40°（对应通道偏移差）
- ✅ `LaserId` 编码：0, 1, ..., 99（第一步），100, 101, ..., 199（第二步）
- ✅ `LaserId` 有序排列（按从小到大）
- ✅ JSON 格式纵向展开，便于阅读

---

## 参考案例

- **ATX_100（实测规格）**：100 通道，10 Hz，120° FOV
  - 生成后应观察到 `AzimuthDeg` 覆盖 -60° ~ +60°（理想扫描角）
  - 总点数：120,000 点/周期（1200 步 × 100 通道）
  - LaserId 范围：0 ~ 119,999（第一周期）

---

## 相关文档

- [lidar_essentials.md](./core/lidar_essentials.md) - 核心规则
- [adjustments.md](../references/adjustments.md) - 修正记录
