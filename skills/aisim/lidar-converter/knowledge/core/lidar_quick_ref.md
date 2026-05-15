# aiSim LiDAR 参数快速参考

## ⚠️ Flash LiDAR 关键注意事项（1D 摆镜扫描）

**生成 ScanningPattern 时的核心规则**：

```python
# ✅ 正确：AzimuthDeg = 扫描角 + 通道偏转（绝对方位角）
for time_step in range(steps):
    scan_az = -horizontal_fov_deg / 2 + time_step * horizontal_resolution_deg
    for channel in channels:
        laser = {
            "AzimuthDeg": scan_az + channel.azimuth_offset,  # 扫描角 + 通道偏转
            "ElevationDeg": channel.elevation,
            "TimeOffsetS": time_step * time_per_step
        }

# ❌ 错误：只写通道偏转会丢失扫描范围
# azimuth = channel.azimuth_offset  # 导出点云方位角会塌缩到 ±几度
```

**验证标准**：
- ✅ `AzimuthDeg` 范围应接近水平 FOV（例如 ATX_100 约 ±60°，并叠加通道偏转）
- ✅ `TimeOffsetS` 覆盖 1/frame_rate 秒（多周期则跨周期递增）
- ❌ 如果 `AzimuthDeg` 范围仅在 ±5° 左右，说明 pattern 丢失了扫描角

---

## Rotating LiDAR 必需参数
- rpm
- laser_count
- vertical_fov_min_deg
- vertical_fov_max_deg
- horizontal_resolution_deg
- distance_min_meter
- distance_max_meter

## Flash LiDAR 必需参数
- frame_rate
- horizontal_fov_deg
- vertical_fov_deg
- horizontal_resolution_deg
- vertical_resolution_deg
- distance_min_meter
- distance_max_meter

## 提取关键词（中英文）

**RPM/转速:** RPM, rotations per minute, rotation speed, 转速, 旋转速度

**Frame Rate/帧率:** frame rate, framerate, fps, Hz, frequency, 帧率, 频率

**Channels/通道数:** channels, lasers, beams, laser count, 通道, 线数, 激光束

**Vertical FOV/垂直视场:** vertical FOV, V-FOV, elevation range, 垂直视场角, 垂直角度

**Horizontal FOV/水平视场:** horizontal FOV, H-FOV, azimuth range, 水平视场角, 水平角度

**Range/测距范围:** range, distance, detection range, 测距, 探测距离, 量程

**Resolution/分辨率:** resolution, angular resolution, step, 分辨率, 角分辨率

## 默认值
- distance_min_meter: 0.3
- distance_max_meter: 200.0
- distance_accuracy_meter: 0.0
- horizontal_resolution_deg: 0.2

## 计算公式
- **Rotating update_intervals:** 60,000,000 / rpm (微秒)
- **Flash update_intervals:** 1,000,000 / frame_rate (微秒)

## 文件路径格式
```
"scanning_pattern_file": "calibrations://scanning_pattern/[LidarName]_pattern.json"
```

## 配置结构约定（本项目）

- LiDAR 参数统一放在 `lidar_config` 内（包括 `max_stored_cycles`、`scanning_pattern_file` 等），避免平铺到 `lidar_sensor`。
- Rotating/Flash 统一使用 `"type": "lidar"`（由 `lidar_config.rpm` vs `lidar_config.frame_rate` 区分）。
- `lidar_config.frame_rate` 使用整数 Hz。
