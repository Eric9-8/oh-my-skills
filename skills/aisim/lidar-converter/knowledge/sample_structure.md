STRICTLY FOLLOW ONE OF THE TWO TEMPLATES BELOW BASED ON LIDAR TYPE.
DO NOT MIX KEYS. PRESERVE THE NESTED STRUCTURE ("sensors" -> "lidar_sensor").
IMPORTANT: Put LiDAR parameters under "lidar_config" (including "max_stored_cycles").
IMPORTANT: Both ROTATING and FLASH LiDAR use the same sensor "type": "lidar".
IMPORTANT: "frame_rate" must be an INT (Hz).

--- OPTION A: ROTATING LIDAR TEMPLATE (Mechanical) ---
Use this if the LiDAR spins (has RPM).
{
  "sensors": {
    "lidar_sensor": {
      "type": "lidar",
      "update_intervals": [ 40000 ],
      "mounting": {
        "position": [ 1.0, 0.0, 3.0 ],
        "rotation": { "pitch": 0.0, "roll": 0.0, "yaw": 0.0 }
      },
      "lidar_config": {
        "max_stored_cycles": 2,
        "distance_min_meter": 0.3,
        "distance_max_meter": 200.0,
        "distance_accuracy_meter": 0.0,
        "horizontal_resolution_deg": 0.2,
        "laser_count": 64,
        "vertical_fov_min_deg": -25.0,
        "vertical_fov_max_deg": 15.0,
        "rpm": 1200,
        "scanning_pattern_file": "calibrations://scanning_pattern/YOUR_FILENAME_HERE.json",
        "visualization": {
          "enabled": false,
          "color": [ 255, 0, 0 ],
          "point_size": 40.0
        }
      }
    }
  }
}

--- OPTION B: FLASH/SOLID-STATE LIDAR TEMPLATE ---
Use this if the LiDAR is MEMS/Flash/Hybrid (has Frame Rate, fixed FOV).
{
  "sensors": {
    "lidar_sensor": {
      "type": "lidar",
      "update_intervals": [ 40000 ],
      "mounting": {
        "position": [ 1.0, 0.0, 3.0 ],
        "rotation": { "pitch": 0.0, "roll": 0.0, "yaw": 0.0 }
      },
      "lidar_config": {
        "max_stored_cycles": 2,
        "distance_min_meter": 0.5,
        "distance_max_meter": 200.0,
        "distance_accuracy_meter": 0.0,
        "vertical_resolution_deg": 0.2,
        "horizontal_resolution_deg": 0.2,
        "vertical_fov_deg": 30,
        "horizontal_fov_deg": 80,
        "scanning_pattern_file": "calibrations://scanning_pattern/YOUR_FILENAME_HERE.json",
        "frame_rate": 25,
        "visualization": {
          "enabled": true,
          "color": [ 255, 0, 0 ],
          "point_size": 40.0
        }
      }
    }
  }
}
