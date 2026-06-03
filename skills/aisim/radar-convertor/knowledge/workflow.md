# Radar Convertor Workflow

## Inputs

- aiSim 6-radar Advanced export directory.
- `RadarService_format.json`.
- Optional real MCAP for comparison.

## Export Gate

Before conversion:
- six sensor directories must exist under `ego/`;
- each sensor must have at least 800 JSON frames;
- frame numbers should be continuous;
- each frame should include `captured_objects` and `targets`;
- Advanced target `rcs/snr/id` should be valid.

## Conversion Gate

Use:

```bash
python3 scripts/radar_to_mcap.py \
  --input-dir <export>/ego \
  --output output/sim_radar_6radar_800f.mcap \
  --source objects_with_targets \
  --expected-frames 800 \
  --frame-limit 800 \
  --format templates/RadarService_format.json
```

Expected result:
- 6 topics;
- 800 messages/topic;
- 4800 total messages;
- 2012B payloads.

## Validation Gate

Run:

```bash
python3 scripts/validate_radar_mcap.py \
  --input output/sim_radar_6radar_800f.mcap \
  --format templates/RadarService_format.json \
  --expected-count 800
```

## Comparison Gate

Run:

```bash
python3 scripts/compare_radar_mcap.py \
  --real <real.mcap> \
  --sim output/sim_radar_6radar_800f.mcap \
  --format templates/RadarService_format.json \
  --real-count 800 \
  --sim-count 800 \
  --output output/radar_6radar_validation_report.md
```

The report must expose remaining gaps instead of smoothing them over.
