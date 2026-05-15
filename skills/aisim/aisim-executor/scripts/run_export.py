#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aisim-executor: run_export.py

aiSim 仿真执行与传感器数据导出核心脚本。
封装 aisim_client 调用，支持 LiDAR/Camera/Radar 数据导出和验证。

Usage:
    python3 run_export.py \
        --sensor-config /path/to/config.json \
        --sensor-type lidar \
        --pattern-file /path/to/pattern.json \
        --output-dir /path/to/output \
        --validate

Author: aiSim-agent
Version: 1.3.0
Date: 2026-01-04
"""

import argparse
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Version Detection
# =============================================================================

def detect_aisim_version() -> str:
    """
    Detect installed aiSim version by scanning /opt/aiMotive directory.
    Returns version string like '5.9.0', '5.10.0', etc.
    """
    aisim_base = "/opt/aiMotive"

    # Look for aisim-X.Y.Z directories
    pattern = os.path.join(aisim_base, "aisim-*")
    matches = glob.glob(pattern)

    versions = []
    for path in matches:
        dirname = os.path.basename(path)
        # Extract version from aisim-X.Y.Z
        match = re.match(r"aisim-(\d+\.\d+\.\d+)", dirname)
        if match:
            versions.append(match.group(1))

    if not versions:
        return "5.9.0"  # Default fallback

    # Sort by version and return the latest
    versions.sort(key=lambda v: [int(x) for x in v.split(".")])
    return versions[-1]


def detect_tc_core_version() -> str:
    """
    Detect installed tc_core toolchain version.
    Returns version string like '5.9.0', '5.10.0', etc.
    """
    tc_base = "/opt/aiMotive/toolchains"

    pattern = os.path.join(tc_base, "tc_core-*")
    matches = glob.glob(pattern)

    versions = []
    for path in matches:
        dirname = os.path.basename(path)
        match = re.match(r"tc_core-(\d+\.\d+\.\d+)", dirname)
        if match:
            versions.append(match.group(1))

    if not versions:
        return "5.9.0"  # Default fallback

    versions.sort(key=lambda v: [int(x) for x in v.split(".")])
    return versions[-1]


# =============================================================================
# Constants (with auto-detection)
# =============================================================================

# Auto-detect versions or use environment variables
AISIM_VERSION = os.environ.get("AISIM_VERSION", detect_aisim_version())
TC_CORE_VERSION = os.environ.get("TC_CORE_VERSION", detect_tc_core_version())

# System paths (can be overridden by environment variables)
AISIM_HOME = os.environ.get("AISIM_HOME", f"/opt/aiMotive/aisim-{AISIM_VERSION}")
AISIM_GUI_HOME = os.environ.get("AISIM_GUI_HOME", f"/opt/aiMotive/aisim_gui-{AISIM_VERSION}")
TC_CORE_HOME = os.environ.get("TC_CORE_HOME", f"/opt/aiMotive/toolchains/tc_core-{TC_CORE_VERSION}")

# Derived paths
AISIM_BIN = f"{AISIM_HOME}/bin/aisim"
AISIM_CLIENT = f"{TC_CORE_HOME}/clients/bin/aisim_client"
CALIBRATIONS_DIR = f"{AISIM_GUI_HOME}/data/calibrations"
SCANNING_PATTERN_DIR = f"{CALIBRATIONS_DIR}/scanning_pattern"
SCENARIOS_DIR = f"{AISIM_GUI_HOME}/data/openscenarios"

# Service name (with full version)
AISIM_SERVICE = f"aisim-{AISIM_VERSION}.service"

# Defaults
DEFAULT_MAP = "TestTrack_Synth_SensorCalibrationStation"
DEFAULT_SCENARIO = f"{SCENARIOS_DIR}/TestTrack_Synth_SensorCalibrationStation_demo.xosc"
DEFAULT_SERVER = "127.0.0.1"
DEFAULT_PORT = 8888
DEFAULT_TICK_US = 10000  # 推荐：10ms（导出必须使用 stepped + update_interval 整除约束）

# Validation script paths (relative to this script)
SCRIPT_DIR = Path(__file__).parent.resolve()
LIDAR_VALIDATOR = SCRIPT_DIR.parent.parent / "lidar-converter" / "scripts" / "validate_las_pattern.py"
CAMERA_VALIDATOR = SCRIPT_DIR.parent.parent / "camera-converter" / "scripts" / "validate_camera_distortion.py"

# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_NOT_FOUND = 1
EXIT_SERVER_NOT_RUNNING = 2
EXIT_CLIENT_FAILED = 3
EXIT_EXPORT_EMPTY = 4
EXIT_VALIDATION_FAILED = 5
EXIT_PERMISSION_DENIED = 10
EXIT_UNKNOWN_ERROR = 99


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ExportConfig:
    """Export configuration parameters."""
    sensor_type: str
    start_step: int = 5
    end_step: int = 20
    export_step: int = 1


@dataclass
class ExecutionResult:
    """Result of the execution process."""
    success: bool
    exit_code: int
    message: str
    exported_files: List[str] = field(default_factory=list)
    validation_report: Optional[str] = None
    execution_time_sec: float = 0.0
    client_output: str = ""
    client_errors: str = ""


# =============================================================================
# Utility Functions
# =============================================================================

def log_info(msg: str) -> None:
    """Print info message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO: {msg}")


def log_error(msg: str) -> None:
    """Print error message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {msg}", file=sys.stderr)


def log_warning(msg: str) -> None:
    """Print warning message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] WARNING: {msg}", file=sys.stderr)


def check_server_running(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if aiSim server is running by attempting to connect."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.error:
        return False


def wait_for_server(host: str, port: int, max_wait: int = 30) -> bool:
    """Wait for server to become available."""
    log_info(f"Waiting for aiSim server at {host}:{port}...")
    for i in range(max_wait):
        if check_server_running(host, port):
            log_info(f"Server is ready (waited {i} seconds)")
            return True
        time.sleep(1)
        if (i + 1) % 5 == 0:
            log_info(f"Still waiting... ({i + 1}/{max_wait} seconds)")
    return False


def parse_server_address(address: str) -> Tuple[str, int]:
    """Parse server address string into host and port."""
    if ":" in address:
        parts = address.split(":")
        return parts[0], int(parts[1])
    return address, DEFAULT_PORT


# =============================================================================
# Path Management
# =============================================================================

def resolve_pattern_path(
    sensor_config_path: Path,
    pattern_file_path: Optional[Path],
    temp_dir: Path
) -> Tuple[Path, Optional[Path]]:
    """
    Resolve pattern file path for aisim_client.

    aisim_client does NOT resolve relative paths from the config file directory.
    Therefore, we must use absolute paths for the scanning_pattern_file reference.

    This function:
    1. Creates a 'scanning_pattern/' subdirectory in temp_dir
    2. Creates a symlink (or copies) the pattern file there
    3. Updates the config to use ABSOLUTE path to the pattern file
    4. Returns the modified config path

    Returns:
        Tuple of (modified_config_path, pattern_copy_path_or_none)
    """
    # Read sensor config
    with open(sensor_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Find lidar_config and scanning_pattern_file
    lidar_config = None
    for sensor_name, sensor_data in config.get("sensors", {}).items():
        if sensor_data.get("type") == "lidar" and "lidar_config" in sensor_data:
            lidar_config = sensor_data["lidar_config"]
            break

    if not lidar_config:
        log_warning("No lidar_config found in sensor configuration")
        return sensor_config_path, None

    pattern_ref = lidar_config.get("scanning_pattern_file", "")

    # Determine the actual pattern file to use
    actual_pattern_path = None

    if pattern_file_path and pattern_file_path.exists():
        # Use the explicitly provided pattern file
        actual_pattern_path = pattern_file_path
        pattern_name = pattern_file_path.name
    elif pattern_ref:
        # Try to extract pattern name from calibrations:// reference
        # Format: calibrations://scanning_pattern/XXX.json
        if "scanning_pattern/" in pattern_ref:
            pattern_name = pattern_ref.split("scanning_pattern/")[-1]
            # Look for the pattern file in various locations
            search_paths = [
                Path(SCANNING_PATTERN_DIR) / pattern_name,
                sensor_config_path.parent / "scanning_pattern" / pattern_name,
                sensor_config_path.parent / pattern_name,
            ]
            for search_path in search_paths:
                if search_path.exists():
                    actual_pattern_path = search_path
                    log_info(f"Found pattern file at: {actual_pattern_path}")
                    break
        else:
            pattern_name = os.path.basename(pattern_ref)

    if not actual_pattern_path:
        log_warning(f"Pattern file not found. Reference: {pattern_ref}")
        log_warning("Please provide --pattern-file argument or ensure file exists")
        return sensor_config_path, None

    # Create scanning_pattern subdirectory in temp_dir
    pattern_subdir = temp_dir / "scanning_pattern"
    pattern_subdir.mkdir(parents=True, exist_ok=True)

    # Copy or link the pattern file to temp dir
    target_pattern_path = pattern_subdir / pattern_name
    if not target_pattern_path.exists():
        try:
            # Try symlink first (faster, saves disk space)
            target_pattern_path.symlink_to(actual_pattern_path.resolve())
            log_info(f"Created symlink: {target_pattern_path} -> {actual_pattern_path}")
        except (OSError, PermissionError):
            # Fall back to copy
            shutil.copy2(actual_pattern_path, target_pattern_path)
            log_info(f"Copied pattern file to: {target_pattern_path}")

    # Update config to use absolute path (aisim_client does NOT resolve relative paths from config dir)
    new_pattern_ref = str(target_pattern_path.resolve())
    lidar_config["scanning_pattern_file"] = new_pattern_ref
    log_info(f"Updated scanning_pattern_file to absolute path: {new_pattern_ref}")

    # Write modified config to temp directory
    modified_config_path = temp_dir / sensor_config_path.name
    with open(modified_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    log_info(f"Created working config: {modified_config_path}")

    return modified_config_path, target_pattern_path


def cleanup_symlink(symlink_path: Optional[Path]) -> None:
    """Remove symlink if it was created by us."""
    if symlink_path and symlink_path.is_symlink():
        try:
            symlink_path.unlink()
            log_info(f"Cleaned up symlink: {symlink_path}")
        except Exception as e:
            log_warning(f"Failed to cleanup symlink: {e}")


# =============================================================================
# Export Configuration Generation
# =============================================================================

def generate_export_config(
    sensor_type: str,
    export_config: ExportConfig,
    output_path: Path,
    sensor_config_path: Optional[Path] = None
) -> Path:
    """Generate export configuration JSON file."""

    if sensor_type == "lidar":
        config = {
            "vehicles": {
                "ego": {
                    "sensors": [
                        {
                            "sensor_name": "lidar_sensor",
                            "subtypes": [
                                {"subtype_name": "las", "extension": "las"},
                                {"subtype_name": "json", "extension": "json"}
                            ]
                        }
                    ],
                    "export_step": export_config.export_step,
                    "start": export_config.start_step,
                    "end": export_config.end_step
                }
            }
        }
    elif sensor_type == "camera":
        # Read camera names from sensor config
        camera_sensors = []
        if sensor_config_path and sensor_config_path.exists():
            with open(sensor_config_path, "r", encoding="utf-8") as f:
                sensor_data = json.load(f)
            for sensor_name, sensor_info in sensor_data.get("sensors", {}).items():
                if sensor_info.get("type") == "camera":
                    camera_sensors.append({
                        "sensor_name": sensor_name,
                        "subtypes": [
                            {"subtype_name": "color", "extension": "tga"}
                        ]
                    })

        if not camera_sensors:
            # Fallback to default
            camera_sensors = [{
                "sensor_name": "camera_sensor",
                "subtypes": [
                    {"subtype_name": "color", "extension": "tga"},
                    {"subtype_name": "seg", "extension": "tga"}
                ]
            }]

        config = {
            "vehicles": {
                "ego": {
                    "sensors": camera_sensors,
                    "export_step": export_config.export_step,
                    "start": export_config.start_step,
                    "end": export_config.end_step
                }
            }
        }
    elif sensor_type == "radar":
        config = {
            "vehicles": {
                "ego": {
                    "sensors": [
                        {
                            "sensor_name": "radar_sensor",
                            "subtypes": [
                                {"subtype_name": "radar", "extension": "json"}
                            ]
                        }
                    ],
                    "export_step": export_config.export_step,
                    "start": export_config.start_step,
                    "end": export_config.end_step
                }
            }
        }
    else:
        raise ValueError(f"Unsupported sensor type: {sensor_type}")

    export_config_path = output_path / f"{sensor_type}_export_config.json"
    with open(export_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    log_info(f"Generated export config: {export_config_path}")
    return export_config_path


# =============================================================================
# aiSim Client Execution
# =============================================================================

def build_aisim_client_command(
    sensor_config: Path,
    export_config: Path,
    output_dir: Path,
    server_address: str,
    map_name: str,
    scenario_path: Path,
    tick_us: int,
    environment_config: Optional[Path] = None,
    extra_args: Optional[List[str]] = None
) -> List[str]:
    """Build aisim_client command line arguments."""

    cmd = [
        AISIM_CLIENT,
        f"--address={server_address}",
        f"--sensor_configuration={sensor_config}",
        f"--map={map_name}",
        f"--scenario={scenario_path}",
        "--open_scenario",
        f"--stepped={tick_us}",  # Export requires stepped (non-realtime) simulation
        f"--world_update_interval={tick_us}",  # Must divide evenly into sensor update_intervals
        f"--scenario_update_interval={tick_us}",  # Keep scenario actions in sync with world tick
        "--engine_raytrace_backend=vulkan",  # LiDAR requires VULKAN raytrace backend
        "--export",
        f"--export_configuration={export_config}",
        f"--output_dir={output_dir}",
        "--exit_after_export_end",
        "--no_draw",
    ]

    if environment_config:
        cmd.append(f"--environment_config_path={environment_config}")

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def execute_aisim_client(
    cmd: List[str],
    timeout: int = 300,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    """Execute aisim_client and capture output.

    Args:
        cmd: Command and arguments to execute
        timeout: Maximum execution time in seconds
        cwd: Working directory (important: aisim_client uses relative paths like ../data/)
    """

    log_info(f"Executing: {' '.join(cmd)}")
    if cwd:
        log_info(f"Working directory: {cwd}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )

        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr

    except subprocess.TimeoutExpired:
        process.kill()
        return -1, "", "Process timed out"
    except Exception as e:
        return -1, "", str(e)


# =============================================================================
# Validation
# =============================================================================

def find_exported_files(output_dir: Path, sensor_type: str) -> List[Path]:
    """Find exported files in output directory (recursive search)."""

    if sensor_type == "lidar":
        pattern = "**/*.las"
    elif sensor_type == "camera":
        pattern = "**/*.tga"
    elif sensor_type == "radar":
        pattern = "**/*radar*.json"
    else:
        pattern = "**/*"

    files = list(output_dir.glob(pattern))
    # Sort by name to get consistent ordering
    files.sort(key=lambda x: x.name)
    return files


def run_lidar_validation(
    las_file: Path,
    sensor_config: Path,
    output_dir: Path
) -> Tuple[bool, str]:
    """Run LiDAR validation script."""

    if not LIDAR_VALIDATOR.exists():
        log_warning(f"LiDAR validator not found: {LIDAR_VALIDATOR}")
        return False, "Validator script not found"

    report_path = output_dir / "validation_report.md"

    cmd = [
        sys.executable,
        str(LIDAR_VALIDATOR),
        "--las", str(las_file),
        "--config", str(sensor_config),
        "--out", str(report_path)
    ]

    log_info(f"Running validation: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and report_path.exists():
            return True, str(report_path)
        else:
            return False, result.stderr or "Validation failed"

    except Exception as e:
        return False, str(e)


def run_camera_validation(
    image_dir: Path,
    sensor_config: Path,
    output_dir: Path
) -> Tuple[bool, str]:
    """Run Camera validation script."""

    if not CAMERA_VALIDATOR.exists():
        log_warning(f"Camera validator not found: {CAMERA_VALIDATOR}")
        return False, "Validator script not found"

    report_path = output_dir / "distortion_report.md"

    cmd = [
        sys.executable,
        str(CAMERA_VALIDATOR),
        "--image-dir", str(image_dir),
        "--config", str(sensor_config),
        "--out", str(report_path)
    ]

    log_info(f"Running validation: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and report_path.exists():
            return True, str(report_path)
        else:
            return False, result.stderr or "Validation failed"

    except Exception as e:
        return False, str(e)


# =============================================================================
# Report Generation
# =============================================================================

def generate_execution_summary(
    result: ExecutionResult,
    args: argparse.Namespace,
    output_dir: Path
) -> Path:
    """Generate execution summary JSON file."""

    summary = {
        "timestamp": datetime.now().isoformat(),
        "success": result.success,
        "exit_code": result.exit_code,
        "message": result.message,
        "execution_time_sec": result.execution_time_sec,
        "parameters": {
            "sensor_config": str(args.sensor_config),
            "sensor_type": args.sensor_type,
            "pattern_file": str(args.pattern_file) if args.pattern_file else None,
            "output_dir": str(output_dir),
            "server": args.server,
            "map": args.map,
            "scenario": str(args.scenario),
            "export_start": args.export_start,
            "export_end": args.export_end,
            "export_step": args.export_step,
            "validate": args.validate
        },
        "exported_files": result.exported_files,
        "validation_report": result.validation_report
    }

    summary_path = output_dir / "execution_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    log_info(f"Generated execution summary: {summary_path}")
    return summary_path


# =============================================================================
# Main Execution Flow
# =============================================================================

def main(args: argparse.Namespace) -> int:
    """Main execution flow."""

    start_time = time.time()
    result = ExecutionResult(
        success=False,
        exit_code=EXIT_UNKNOWN_ERROR,
        message="Unknown error"
    )

    # Temp directory for intermediate files
    temp_dir = Path(tempfile.mkdtemp(prefix="aisim_executor_"))
    symlink_created = None

    try:
        # =================================================================
        # Step 1: Validate inputs
        # =================================================================
        log_info("=" * 60)
        log_info("Step 1: Validating inputs")
        log_info("=" * 60)

        sensor_config_path = Path(args.sensor_config).resolve()
        if not sensor_config_path.exists():
            log_error(f"Sensor config not found: {sensor_config_path}")
            result.exit_code = EXIT_CONFIG_NOT_FOUND
            result.message = f"Sensor config not found: {sensor_config_path}"
            return result.exit_code

        pattern_file_path = None
        if args.pattern_file:
            pattern_file_path = Path(args.pattern_file).resolve()
            if not pattern_file_path.exists():
                log_error(f"Pattern file not found: {pattern_file_path}")
                result.exit_code = EXIT_CONFIG_NOT_FOUND
                result.message = f"Pattern file not found: {pattern_file_path}"
                return result.exit_code

        # Validate sensor type
        if args.sensor_type not in ["lidar", "camera", "radar"]:
            log_error(f"Invalid sensor type: {args.sensor_type}")
            result.exit_code = EXIT_CONFIG_NOT_FOUND
            result.message = f"Invalid sensor type: {args.sensor_type}"
            return result.exit_code

        log_info(f"Sensor config: {sensor_config_path}")
        log_info(f"Sensor type: {args.sensor_type}")
        log_info(f"Pattern file: {pattern_file_path or 'N/A'}")

        # =================================================================
        # Step 2: Setup output directory
        # =================================================================
        log_info("=" * 60)
        log_info("Step 2: Setting up output directory")
        log_info("=" * 60)

        if args.output_dir:
            output_dir = Path(args.output_dir).resolve()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path.cwd() / "output" / f"export_{timestamp}"

        output_dir.mkdir(parents=True, exist_ok=True)
        log_info(f"Output directory: {output_dir}")

        # =================================================================
        # Step 3: Handle pattern file path
        # =================================================================
        log_info("=" * 60)
        log_info("Step 3: Processing pattern file")
        log_info("=" * 60)

        try:
            working_config, symlink_created = resolve_pattern_path(
                sensor_config_path,
                pattern_file_path,
                temp_dir
            )
            log_info(f"Working config: {working_config}")
        except PermissionError:
            result.exit_code = EXIT_PERMISSION_DENIED
            result.message = "Permission denied when creating symlink"
            return result.exit_code

        # =================================================================
        # Step 4: Check aiSim server (skip in dry-run mode)
        # =================================================================
        log_info("=" * 60)
        log_info("Step 4: Checking aiSim server")
        log_info("=" * 60)

        host, port = parse_server_address(args.server)

        if args.dry_run:
            log_info("DRY RUN - Skipping server check")
        elif not check_server_running(host, port):
            log_warning(f"aiSim server not running at {host}:{port}")
            log_info("Please start the server using one of:")
            log_info(f"  1. sudo systemctl start {AISIM_SERVICE}")
            log_info(f"  2. {AISIM_BIN}")

            if not wait_for_server(host, port, max_wait=30):
                log_error("aiSim server did not start within timeout")
                result.exit_code = EXIT_SERVER_NOT_RUNNING
                result.message = "aiSim server not running"
                return result.exit_code
        else:
            log_info(f"aiSim server is running at {host}:{port}")

        # =================================================================
        # Step 5: Generate export configuration
        # =================================================================
        log_info("=" * 60)
        log_info("Step 5: Generating export configuration")
        log_info("=" * 60)

        export_cfg = ExportConfig(
            sensor_type=args.sensor_type,
            start_step=args.export_start,
            end_step=args.export_end,
            export_step=args.export_step
        )

        export_config_path = generate_export_config(
            args.sensor_type,
            export_cfg,
            temp_dir,
            sensor_config_path
        )

        # =================================================================
        # Step 6: Execute aisim_client
        # =================================================================
        log_info("=" * 60)
        log_info("Step 6: Executing aisim_client")
        log_info("=" * 60)

        scenario_path = Path(args.scenario)
        if not scenario_path.is_absolute():
            scenarios_dir = Path(SCENARIOS_DIR)
            candidate = scenarios_dir / args.scenario
            if candidate.exists():
                scenario_path = candidate
            elif not scenario_path.suffix:
                candidate_with_ext = scenarios_dir / f"{args.scenario}.xosc"
                if candidate_with_ext.exists():
                    scenario_path = candidate_with_ext

        if not scenario_path.exists():
            log_error(f"Scenario file not found: {scenario_path}")
            result.exit_code = EXIT_CONFIG_NOT_FOUND
            result.message = f"Scenario not found: {scenario_path}"
            return result.exit_code
        scenario_path = scenario_path.resolve()

        tick_us = int(args.tick_us)
        if tick_us <= 0:
            log_error(f"Invalid --tick-us: {tick_us} (must be > 0)")
            result.exit_code = EXIT_CONFIG_NOT_FOUND
            result.message = f"Invalid --tick-us: {tick_us}"
            return result.exit_code

        # Ensure sensor update_interval is divisible by tick (aiSim constraint)
        try:
            working_conf = json.loads(working_config.read_text(encoding="utf-8"))
            lidar_sensor = working_conf.get("sensors", {}).get("lidar_sensor", {})
            update_intervals = lidar_sensor.get("update_intervals")
            if isinstance(update_intervals, list) and update_intervals:
                sensor_update_us = int(update_intervals[0])
                if sensor_update_us > 0 and sensor_update_us % tick_us != 0:
                    log_error(
                        "tick 与传感器 update_intervals 不整除："
                        f" update_intervals[0]={sensor_update_us}us, tick={tick_us}us"
                    )
                    result.exit_code = EXIT_CONFIG_NOT_FOUND
                    result.message = "tick_us must evenly divide sensor update_intervals[0]"
                    return result.exit_code
        except Exception as e:
            log_warning(f"Failed to validate tick vs update_intervals: {e}")

        # Resolve environment config path if provided
        environment_config_path = None
        if args.environment_config:
            environment_config_path = Path(args.environment_config).resolve()
            if not environment_config_path.exists():
                log_warning(f"Environment config not found: {environment_config_path}")
                environment_config_path = None

        cmd = build_aisim_client_command(
            sensor_config=working_config,
            export_config=export_config_path,
            output_dir=output_dir,
            server_address=f"{host}:{port}",
            map_name=args.map,
            scenario_path=scenario_path,
            tick_us=tick_us,
            environment_config=environment_config_path,
        )

        if args.dry_run:
            log_info("DRY RUN - Command would be:")
            log_info(" ".join(cmd))
            result.success = True
            result.exit_code = EXIT_SUCCESS
            result.message = "Dry run completed"
            return result.exit_code

        # Execute from aisim_client's directory so relative paths (../data/) work correctly
        aisim_client_dir = os.path.dirname(AISIM_CLIENT)
        returncode, stdout, stderr = execute_aisim_client(
            cmd,
            timeout=int(args.client_timeout_sec),
            cwd=aisim_client_dir,
        )
        result.client_output = stdout
        result.client_errors = stderr

        # Save execution log
        log_file = output_dir / "execution_log.txt"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Working directory: {aisim_client_dir}\n")
            f.write(f"Return code: {returncode}\n")
            f.write(f"\n{'='*60}\nSTDOUT:\n{'='*60}\n{stdout}\n")
            f.write(f"\n{'='*60}\nSTDERR:\n{'='*60}\n{stderr}\n")

        if returncode != 0:
            log_error(f"aisim_client failed with exit code {returncode}")
            log_error(f"See log: {log_file}")
            result.exit_code = EXIT_CLIENT_FAILED
            result.message = f"aisim_client failed: {stderr[:200] if stderr else 'unknown error'}"
            return result.exit_code

        log_info("aisim_client completed successfully")

        # =================================================================
        # Step 7: Find exported files
        # =================================================================
        log_info("=" * 60)
        log_info("Step 7: Checking exported files")
        log_info("=" * 60)

        exported_files = find_exported_files(output_dir, args.sensor_type)
        result.exported_files = [str(f) for f in exported_files]

        if not exported_files:
            log_warning("No exported files found!")
            result.exit_code = EXIT_EXPORT_EMPTY
            result.message = "No exported files found"
            # Continue to generate summary even if no files
        else:
            log_info(f"Found {len(exported_files)} exported file(s):")
            for f in exported_files[:5]:  # Show first 5
                log_info(f"  - {f.name}")
            if len(exported_files) > 5:
                log_info(f"  ... and {len(exported_files) - 5} more")

        # =================================================================
        # Step 8: Run validation (if enabled)
        # =================================================================
        if args.validate and exported_files:
            log_info("=" * 60)
            log_info("Step 8: Running validation")
            log_info("=" * 60)

            if args.sensor_type == "lidar":
                # Use the first LAS file for validation
                las_file = exported_files[0]
                success, report_or_error = run_lidar_validation(
                    las_file,
                    sensor_config_path,  # Use original config for validation
                    output_dir
                )

                if success:
                    result.validation_report = report_or_error
                    log_info(f"Validation report: {report_or_error}")
                else:
                    log_warning(f"Validation failed: {report_or_error}")
                    result.exit_code = EXIT_VALIDATION_FAILED
                    result.message = f"Validation failed: {report_or_error}"
            elif args.sensor_type == "camera":
                # Find the exports directory containing camera images
                # Structure: output_dir/exports/<timestamp>/ego/<camera_name>/color/*.tga
                exports_dir = output_dir / "exports"
                if exports_dir.exists():
                    # Find the latest export timestamp directory
                    timestamp_dirs = sorted(exports_dir.iterdir(), reverse=True)
                    if timestamp_dirs:
                        ego_dir = timestamp_dirs[0] / "ego"
                        if ego_dir.exists():
                            success, report_or_error = run_camera_validation(
                                ego_dir,
                                sensor_config_path,
                                output_dir
                            )

                            if success:
                                result.validation_report = report_or_error
                                log_info(f"Validation report: {report_or_error}")
                            else:
                                log_warning(f"Validation failed: {report_or_error}")
                                # Camera validation failure is a warning, not an error
                                # because distortion validation depends on scene content
                        else:
                            log_warning("No ego directory found in exports")
                    else:
                        log_warning("No timestamp directories found in exports")
                else:
                    log_warning("No exports directory found")
            else:
                log_info(f"Validation not yet implemented for {args.sensor_type}")

        # =================================================================
        # Success
        # =================================================================
        if result.exit_code == EXIT_UNKNOWN_ERROR:  # Not set by earlier errors
            result.success = True
            result.exit_code = EXIT_SUCCESS
            result.message = f"Export completed. {len(exported_files)} file(s) exported."

    except Exception as e:
        log_error(f"Unexpected error: {e}")
        result.exit_code = EXIT_UNKNOWN_ERROR
        result.message = str(e)
        import traceback
        traceback.print_exc()

    finally:
        # =================================================================
        # Cleanup and summary
        # =================================================================
        result.execution_time_sec = time.time() - start_time

        log_info("=" * 60)
        log_info("Execution Summary")
        log_info("=" * 60)
        log_info(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
        log_info(f"Exit code: {result.exit_code}")
        log_info(f"Message: {result.message}")
        log_info(f"Execution time: {result.execution_time_sec:.2f} seconds")
        log_info(f"Exported files: {len(result.exported_files)}")

        # Generate summary file
        if 'output_dir' in dir() and output_dir.exists():
            generate_execution_summary(result, args, output_dir)

        # Cleanup
        if not args.no_cleanup:
            if symlink_created and not args.keep_symlink:
                cleanup_symlink(symlink_created)

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    return result.exit_code


# =============================================================================
# CLI Entry Point
# =============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="aiSim Executor - Automated simulation and sensor data export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic LiDAR export with validation
  python3 run_export.py -c config.json -t lidar -p pattern.json -v

  # Export to specific directory
  python3 run_export.py -c config.json -t lidar -o /path/to/output

  # Custom export range
  python3 run_export.py -c config.json -t lidar --export-start 10 --export-end 50

  # Dry run (print command without executing)
  python3 run_export.py -c config.json -t lidar --dry-run
        """
    )

    # Required arguments
    parser.add_argument(
        "-c", "--sensor-config",
        required=True,
        help="Path to sensor configuration JSON file"
    )
    parser.add_argument(
        "-t", "--sensor-type",
        required=True,
        choices=["lidar", "camera", "radar"],
        help="Type of sensor"
    )

    # Optional arguments
    parser.add_argument(
        "-p", "--pattern-file",
        help="Path to scanning pattern file (LiDAR)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory for exported data"
    )
    parser.add_argument(
        "-s", "--server",
        default=f"{DEFAULT_SERVER}:{DEFAULT_PORT}",
        help=f"aiSim server address (default: {DEFAULT_SERVER}:{DEFAULT_PORT})"
    )
    parser.add_argument(
        "-m", "--map",
        default=DEFAULT_MAP,
        help=f"Map name (default: {DEFAULT_MAP})"
    )
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO,
        help=f"Scenario file path (default: {DEFAULT_SCENARIO})"
    )
    parser.add_argument(
        "--tick-us",
        type=int,
        default=DEFAULT_TICK_US,
        help=f"Simulation tick in microseconds; used for stepped/world/scenario update intervals (default: {DEFAULT_TICK_US})"
    )
    parser.add_argument(
        "--client-timeout-sec",
        type=int,
        default=300,
        help="Timeout for aisim_client execution in seconds (default: 300)"
    )
    parser.add_argument(
        "--environment-config",
        help="Path to environment configuration JSON file (e.g., Garage.json for lighting)"
    )

    # Export range
    parser.add_argument(
        "--export-start",
        type=int,
        default=5,
        help="Export start step (default: 5)"
    )
    parser.add_argument(
        "--export-end",
        type=int,
        default=20,
        help="Export end step (default: 20)"
    )
    parser.add_argument(
        "--export-step",
        type=int,
        default=1,
        help="Export step interval (default: 1)"
    )

    # Validation
    parser.add_argument(
        "-v", "--validate",
        action="store_true",
        help="Run validation after export"
    )

    # Other options
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not cleanup temporary files"
    )
    parser.add_argument(
        "--keep-symlink",
        action="store_true",
        help="Keep symlink in calibrations directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print command without executing"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args))
