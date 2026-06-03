# Radar Parameter Mapping

## Model Choice

Default to `AdvancedRadarRaytracer`.

Reasons:
- It outputs `captured_objects`, which map naturally to RadarService object slots.
- With `need_target_list=true`, it also outputs valid `targets` with RCS/SNR/id information.
- Current NeuralRadar samples have insufficient target quality fields for RadarService alignment.

## 6-Radar Layout

| sensor | real role | model assumption | h_fov | v_fov | depth range |
|---|---|---|---:|---:|---:|
| `radar_front` | front long range | FVR30 | 120 | 28 | 0.25~260m |
| `radar_front_left` | front-left side | FVR30/CVR30 side | 150 | 20 | 0.2~160m |
| `radar_front_right` | front-right side | FVR30/CVR30 side | 150 | 20 | 0.2~160m |
| `radar_rear` | rear long range | FVR30 rear | 120 | 28 | 0.25~180m |
| `radar_rear_left` | rear-left side | FVR30/CVR30 side | 150 | 20 | 0.2~160m |
| `radar_rear_right` | rear-right side | FVR30/CVR30 side | 150 | 20 | 0.2~160m |

## aiSim Parameters

| aiSim field | value | meaning |
|---|---:|---|
| `update_intervals` | `[50000]` | 20Hz, matching real MCAP |
| `need_target_list` | `true` | keep Advanced targets for score/velocity aggregation |
| `range_resolution_m` | `0.22` | approximate FVR30 range precision scale |
| `max_num_targets` | `500` | Advanced target limit, not RadarService object slot count |
| `num_beam_samples` | `2500` | raytrace quality/performance parameter |
| `num_reflections` | `5` | aiSim raytrace parameter, not full real multipath |

`azimuth_resolution_deg`, `elevation_resolution_deg`, beam widths, and reflection counts are aiSim raytrace parameters. They are not direct hardware spec equivalents.
