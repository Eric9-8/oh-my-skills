# RAW Camera 前置材料清单

## 概述

如果 Camera 需要原始 RAW 输出（如 `AimRawCFA16`、`ColorBayerRAW12`），需要先收集以下材料来正确配置 `dynamic_image_sensor_parameters` 和 `raw_transform`。

---

## 必需材料清单

### 1. 数据格式与端序

| 项目 | 说明 | 示例值 |
|------|------|--------|
| **端序** | RAW 数据是大端序（Big Endian）还是小端序（Little Endian） | Little Endian |
| **位对齐** | ISP 期望 LSB Aligned（低位对齐）还是 MSB Aligned（高位对齐） | MSB Aligned |
| **有效位宽** | RAW12 的有效数据位在 [0-11] 还是 [4-15] | [4-15] (MSB) |

### 2. 传感器物理参数

| 项目 | 说明 | 示例值 | 用于计算 |
|------|------|--------|----------|
| **Pixel Size** | 像素尺寸（微米） | 3.0 µm | `rgb_radiant_exposure_to_voltage` |
| **QE 量子效率** | R/G/B 三通道在峰值波长下的量子效率（%） | R:45%, G:55%, B:40% | `rgb_radiant_exposure_to_voltage` |
| **转换增益 CG** | Conversion Gain（微伏/电子） | 80 µV/e⁻ | `rgb_radiant_exposure_to_voltage` |

### 3. 信号处理参数

| 项目 | 说明 | 示例值 | 对应 aiSim 参数 |
|------|------|--------|-----------------|
| **Voltage Swing** | 传感器最大输出电压（伏特） | 1.0 V | `voltage_swing` |
| **Analog Gain** | 模拟增益 | 1.0 | `analog_gain` |
| **Digital Gain** | 数字增益 | 1.0 | `digital_gain` |
| **ADC 位宽** | 模数转换精度 | 12 bit | `adc_bit_precision` |

### 4. 黑电平与 HDR 压缩

| 项目 | 说明 | 示例值 | 对应 aiSim 参数 |
|------|------|--------|-----------------|
| **Black Level** | 黑电平/基底值 | 64 或 256 | `pre_pwl_pedestal` / `post_pwl_pedestal` |
| **黑电平位置** | 是 PWL 压缩前还是压缩后的值 | 压缩后 | 决定放在 pre 还是 post |
| **RAW 类型** | 原生 12bit（Linear）还是 HDR 压缩（PWL） | PWL | 决定是否需要 `pwl_control_points` |

### 5. PWL 压缩参数（仅 HDR 模式需要）

| 项目 | 说明 | 示例值 |
|------|------|--------|
| **输入位宽** | PWL 输入的 x 轴位宽 | 20bit 或 24bit |
| **Knee Points** | PWL 压缩曲线拐点 | [[1024, 512], [4096, 1024], ...] |

### 6. 满阱容量（可选，用于计算 Voltage Swing）

| 项目 | 说明 | 示例值 |
|------|------|--------|
| **FWC** | 满阱容量（电子数） | 8000 e⁻ |
| **工作模式** | LFM 模式还是 Split-Pixel 模式 | LFM |

---

## 参数计算公式

### rgb_radiant_exposure_to_voltage 计算

```python
import math

# 物理常数
h = 6.626e-34  # 普朗克常数 (J·s)
c = 3e8        # 光速 (m/s)

# 传感器参数
pixel_size = 3.0e-6  # 像素尺寸 (m)
wavelengths = [620e-9, 530e-9, 470e-9]  # R/G/B 峰值波长 (m)
quantum_efficiency = [0.45, 0.55, 0.40]  # R/G/B 量子效率
conversion_gain = 80e-6  # 转换增益 (V/e⁻)

rgb_radiant_exposure_to_voltage = []
for i, (wl, qe) in enumerate(zip(wavelengths, quantum_efficiency)):
    photon_energy = h * c / wl
    value = (pixel_size ** 2) / photon_energy * qe * conversion_gain
    rgb_radiant_exposure_to_voltage.append(value)

print(rgb_radiant_exposure_to_voltage)
# 示例输出: [0.000123, 0.000156, 0.000098]
```

### Voltage Swing 计算（从 FWC）

```python
fwc = 8000  # 满阱容量 (e⁻)
conversion_gain = 80e-6  # 转换增益 (V/e⁻)

voltage_swing = fwc * conversion_gain
print(f"Voltage Swing: {voltage_swing} V")
# 示例输出: Voltage Swing: 0.64 V
```

---

## raw_transform 配置示例

### MSB Aligned（高位对齐，12bit 数据放在 [4-15]）

```json
"raw_transform": {
  "bits_per_pixel": 16,
  "bit_swizzle": [
    {
      "src": [0, 11],
      "dst": [4, 15]
    }
  ]
}
```

### LSB Aligned（低位对齐，12bit 数据放在 [0-11]）

```json
"raw_transform": {
  "bits_per_pixel": 16,
  "bit_swizzle": [
    {
      "src": [0, 11],
      "dst": [0, 11]
    }
  ]
}
```

---

## 收集材料的对话模板

当用户需要生成 RAW12 配置时，可以使用以下模板收集信息：

```
为了生成正确的 RAW Camera 配置，请提供以下信息：

**数据格式**
1. RAW 数据端序：大端序 / 小端序？
2. ISP 期望的位对齐：LSB Aligned [0-11] / MSB Aligned [4-15]？

**传感器参数**
3. Pixel Size（像素尺寸）：_____ µm
4. 量子效率 QE（R/G/B）：___% / ___% / ___%
5. 转换增益 CG：_____ µV/e⁻

**信号处理**
6. Voltage Swing：_____ V（或提供 FWC：_____ e⁻）
7. Analog Gain：_____（通常 1.0）
8. Digital Gain：_____（通常 1.0）

**黑电平与 HDR**
9. Black Level：_____（如 64 或 256）
10. RAW 类型：Linear / PWL（HDR 压缩）？
    - 如果是 PWL，请提供 Knee Points 和输入位宽
```

---

## 参考文档

- aiSim 5.9 Camera 文档：`knowledge/aiSim_5.9_Camera.md`
- Raw camera sensor output 章节（第 1479-1511 行）
