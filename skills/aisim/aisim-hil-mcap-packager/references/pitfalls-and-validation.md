# Pitfalls and Validation Notes

## Export and aiSim Runtime Pitfalls

- Correct OpenSCENARIO flag is `--open_scenario_file`, not `--openscenario_file`.
- Do not mix stray single quotes inside `--configurator_args`; it can swallow later args and produce misleading crashes.
- `No JSON output folder was configured` means the exporter task exists but the export config lacks a valid output folder for that sensor/task.
- `sensor_configurations://scanning_pattern/...` must resolve through aiSim's configuration URI rules; broken URI resolution is not a LiDAR writer bug.
- Full perception can exceed local VRAM, especially with 7 cameras + 8 LiDAR + 6 radar on 3DGS maps. Split camera and no-camera exports when VRAM is tight.
- If aiSim VRAM is not released after exporter exits, inspect `/var/log/aisim-5.11.0.log` and `nvidia-smi`. System service can be stopped with `systemctl stop aisim-5.11.0.service`; stuck services may be killed by systemd timeout.
- If a map fails with missing `asset://maps/<name>/...`, compare the asset directory name with internal `map.json`, GLTF, material, texture URI prefixes. `XinzhuangDemo` versus `Xinzhuang_demo` was one concrete failure.
- License network errors can terminate an otherwise healthy export. Always inspect output counts, not just process exit.
- Vehicle JSON may only flush on scenario-driven clean stop; manually killing or disconnecting the exporter can leave vehicle output absent.
- GUI camera TGA exports are large. Keep only the needed frame window before encoding, and prefer `/tmp/aisim_hil_exports` for temporary no-camera outputs.

## Packaging Pitfalls

- Offset arguments are crop offsets only. Output MCAP family timelines must align after cropping.
- Camera payload must be ROS2 CDR `sensor_msgs/msg/Image` with encapsulation and `encoding="h265"`; raw H265 bytes alone are not enough.
- Camera and LiDAR internal header stamp must use the reference relative time domain, not wall-clock epoch time.
- Radar and Vehicle payloads contain multiple local/global time fields; patch all known offsets so they increase with frame time.
- Copy `/recorder/bag_header` and `/recorder/bag_info` from the real reference MCAP when building customer packages. The real package stores camera/LiDAR intrinsic and extrinsic calibration YAML there; do not invent `/camera_info`, `/lidar_info`, or `/tf_static` topics unless the real package has them.
- IMU data comes from aiSim body frame, not CAN raw fields. Use `imu_params.yaml` `r_s2b` and write `v_sensor = R_s2b.T * v_body`. Do not blindly apply `Topic_y = -CAN_y` to aiSim body-frame data.
- Four pano camera streams need per-sensor CRF. Known tuned values: `camera_left_front=18,camera_left_rear=12,camera_right_front=16,camera_right_rear=13` with global `--camera-crf 40`.

## Hard Failure Versus Warning

Hard failures:

- Missing expected raw topic.
- Wrong schema name or message encoding.
- Missing ROS2 CDR encapsulation.
- Wrong fixed payload length.
- Wrong average frequency beyond tolerance.
- Cross-family start/end spread above tolerance.
- Camera H265 cannot be decoded by ffmpeg.
- Radar `frame_id`, `radar_id`, or target count does not match the contract.
- Vehicle/Radar localtime/globaltime fields are not strictly increasing.
- Missing `/recorder/bag_header` or `/recorder/bag_info` calibration metadata for delivery packages.

Acceptable warnings when documented:

- Long-range LiDAR packet count can differ from real dynamic values while payload length/schema/CDR remain fixed.
- Radar `frame_index` can use a different historical baseline; simulation often starts from the crop window baseline.
- Simulated object distribution, noise, occlusion, motion distortion, and 3DGS/PBR rendering semantics are not identical to real sensors.
- The generated MCAP is not a full all-topic replacement if customers subscribe to localization, map, perception, planning, control, diag, function, recorder, or VRM topics.

## Self-Check Checklist

1. Confirm export counts: camera and LiDAR 10 Hz, radar 20 Hz, vehicle IMU/chassis/body 100 Hz, GNSS 5 Hz.
2. Confirm output duration and family time windows are aligned.
3. Run `validate_hil_full_mcap.py`.
4. Run `validate_time_and_calibration.py`.
5. Run `dry_run_validate_hil_full_mcap.py` against the real MCAP.
6. Generate HTML report with `generate_mcap_comparison_report.py`.
7. Inspect warnings and explicitly classify them as structural blockers or semantic differences.
8. Keep final MCAP under the HIL delivery directory, not only under `/tmp`.
