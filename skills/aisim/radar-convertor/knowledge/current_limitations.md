# Current Limitations

## What Works

- 6 RadarService topics can be generated.
- Each generated message has fixed 2012B CDR payload.
- `RadarService_format.json` has been validated against the real radar MCAP.
- aiSim AdvancedRadarRaytracer exports valid `captured_objects` and `targets`.
- `objects_with_targets` can populate velocity and score fields from Advanced targets.

## Main Gaps vs Real MCAP

- Real MCAP has fixed dense slots: front often 40 objects/frame, side radars often 32 objects/frame. aiSim `captured_objects` are much sparser.
- Rear and rear-side objects are sparse in the current scenario.
- `confidence` is still simplified and usually near 98.
- `cluster_dyn_prop` is less diverse than the real data.
- `x_std/y_std/vx_std` are not yet fully modeled.
- The second payload timestamp is not a true recovered CAN/sensor timestamp.
- Extrinsics are `design_default`, not measured calibration.

## Do Not Hide These Gaps

Generated MCAP may be suitable for algorithm replay smoke testing, but not yet for high-fidelity radar perception validation.
