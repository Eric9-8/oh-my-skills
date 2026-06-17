---
name: aisim-hil-mcap-packager
description: Use this skill when packaging aiSim HIL exports into ROS2-profile MCAP files aligned to a real road-test MCAP, including split camera/no-camera exports, H265 camera tuning, LiDAR/Radar/Vehicle topic mapping, IMU alignment, localtime/globaltime repair, recorder calibration metadata, validation, dry-run checks, and HTML self-check reports.
---

# aiSim HIL MCAP Packager

## Purpose

Convert aiSim HIL exporter outputs into MCAP files that mimic the raw camera / lidar / radar / vehicle topics of the real reference MCAP for algorithm replay.

Use this skill for:

- Building full MCAPs from aiSim `my_exporter` or aiSim GUI outputs.
- Combining camera-only and no-camera exports from the same scenario/map.
- Rebuilding vehicle state, IMU/GNSS/chassis/body topics, or full perception MCAPs.
- Checking replay compatibility against the real MCAP contract.
- Producing self-check HTML reports for customer delivery.

## Canonical Paths

Project root:

```text
/home/jialiang/Downloads/Release_5.11.0/Toolchains/example/src/toolchain_example_src-1.0.0
```

Reference and delivery root:

```text
/home/jialiang/Development/哈啰/HIL仿真/HIL仿真
```

Reference MCAP:

```text
/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/mcap数据/1_014_20260511-195513_0.mcap
```

Core scripts:

```text
tools/hil_full_mcap/build_hil_full_mcap.py
tools/hil_full_mcap/validate_hil_full_mcap.py
tools/hil_full_mcap/dry_run_validate_hil_full_mcap.py
tools/hil_full_mcap/validate_time_and_calibration.py
tools/hil_full_mcap/generate_mcap_comparison_report.py
tools/hil_vehicle_state_mcap/vehicle_state_to_mcap.py
```

Calibration files:

```text
/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/整车:相机:lidar内外参/imu_params.yaml
/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/整车:相机:lidar内外参/sensor_params.yaml
```

## Export Strategy

Prefer split exports when the scene is heavy or contains 3DGS content:

1. Camera-only export with `hil_full_perception_camera_only.json`, or GUI camera export.
2. No-camera export with `hil_full_perception_no_camera.json` for LiDAR/Radar/Vehicle.
3. Build one MCAP with `--camera-root` and `--input-root`.

Use full export only when the scene is light enough and VRAM is stable.

From `build/toolchains/toolchain_example-1.0.0/clients/bin`:

```bash
./my_exporter \
  --configurator_args="--open_scenario --open_scenario_file=../data/scenarios/<scenario>.xosc --sensor_configuration=../data/sensor_configurations/hil_full_perception_no_camera.json --start_timeout=200 --simulation_config=../data/simulation_configurations_hil_full_perception.json --stepped --map=<map>" \
  --exporter_args="--config_path=../data/export_configurations/export_hil_full_perception_tmp.json"
```

For camera-only:

```bash
./my_exporter \
  --configurator_args="--open_scenario --open_scenario_file=../data/scenarios/<scenario>.xosc --sensor_configuration=../data/sensor_configurations/hil_full_perception_camera_only.json --start_timeout=200 --simulation_config=../data/simulation_configurations_hil_full_perception.json --stepped --map=<map>" \
  --exporter_args="--config_path=../data/export_configurations/export_hil_full_perception_tmp.json"
```

## Build MCAP

Run from project root. Always provide `--reference-mcap` and `--imu-params` for delivery candidates.

```bash
python3 tools/hil_full_mcap/build_hil_full_mcap.py \
  --input-root /tmp/aisim_hil_exports/<no_camera_export> \
  --camera-root /path/to/camera/export/ego \
  --output "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/<candidate>.mcap" \
  --reference-mcap "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/mcap数据/1_014_20260511-195513_0.mcap" \
  --imu-params "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/整车:相机:lidar内外参/imu_params.yaml" \
  --camera-limit 400 \
  --lidar-limit 400 \
  --radar-limit 800 \
  --vehicle-limit 4001 \
  --camera-crf 40 \
  --camera-crf-overrides camera_left_front=18,camera_left_rear=12,camera_right_front=16,camera_right_rear=13 \
  --mcap-compression none
```

Crop offsets are selection offsets only. After crop, the MCAP timeline must be rebased to the common reference start time; do not preserve aiSim simulation offset in output timestamps.

## Required Validation Gate

A delivery candidate is not ready until all applicable commands pass:

```bash
python3 tools/hil_full_mcap/validate_hil_full_mcap.py --input <candidate.mcap>
```

```bash
python3 tools/hil_full_mcap/validate_time_and_calibration.py --input <candidate.mcap>
```

```bash
python3 tools/hil_full_mcap/dry_run_validate_hil_full_mcap.py \
  --reference "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/mcap数据/1_014_20260511-195513_0.mcap" \
  --candidate <candidate.mcap>
```

Generate an HTML report:

```bash
python3 tools/hil_full_mcap/generate_mcap_comparison_report.py \
  --real "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/mcap数据/1_014_20260511-195513_0.mcap" \
  --highway <highway_candidate.mcap> \
  --city <city_candidate.mcap> \
  --output "/home/jialiang/Development/哈啰/HIL仿真/HIL仿真/<report>.html"
```

## Delivery Contract

Expected raw topics:

- 7 camera H265 topics at 10 Hz.
- 8 LiDAR UDP packet topics at 10 Hz.
- 6 Radar obstacle list topics at 20 Hz.
- Vehicle IMU/chassis/body at 100 Hz, GNSS at 5 Hz.

Use `--mcap-compression none` for customer-facing packages because the real MCAP chunk compression is empty (`{''}`), not zstd. Camera payload is already H265, so MCAP zstd is not needed for normal delivery.

## When To Read The Reference

Read `references/pitfalls-and-validation.md` before changing scripts, diagnosing failed exports, accepting warnings, or delivering a customer package. It records the known pitfalls and the boundary between hard failures and acceptable semantic warnings.
