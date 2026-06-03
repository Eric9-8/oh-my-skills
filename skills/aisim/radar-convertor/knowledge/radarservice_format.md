# RadarService Format

Current format source: reverse engineering from real MCAP payloads and BLF/DBC evidence.

## Confirmed Structure

- Message type: `hv_sensor_msgs/msg/RadarService`
- MCAP message encoding: `cdr`
- Payload size: 2012 bytes
- CDR header: `00010000`
- Frame IDs:
  - `f_radar_data`
  - `fl_radar_data`
  - `fr_radar_data`
  - `r_radar_data`
  - `rl_radar_data`
  - `rr_radar_data`
- Object area:
  - `targets_offset = 72`
  - `target_stride = 48`
  - `target_count = 40`

## Important Fields

Object slot offsets are relative to `targets_offset + index * target_stride`.

| field | offset | type |
|---|---:|---|
| `cluster_id` | 0 | uint8 |
| `confidence` | 4 | float32 |
| `valid_flag` | 8 | uint8 |
| `update_flag` | 9 | uint8 |
| `cluster_dyn_prop` | 10 | uint8 |
| `x_std` | 12 | float32 |
| `y_std` | 16 | float32 |
| `vx_std` | 20 | float32 |
| `ax_or_vx_abs` | 24 | float32 |
| `cluster_rcs` | 28 | float32 |
| `cluster_dist_long` | 32 | float32 |
| `cluster_dist_lat` | 36 | float32 |
| `cluster_vrel_long` | 40 | float32 |
| `cluster_vrel_lat` | 44 | float32 |

The private IDL is still unavailable. Do not claim this is an official schema.
