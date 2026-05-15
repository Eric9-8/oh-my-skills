#!/usr/bin/env python3
"""
批量更新 aiSim 摄像头配置文件

功能：
- 从 Excel 文件读取外参(位置和旋转)
- 从 YAML 文件读取内参(焦距、主点、畸变参数), 支持Pinhole和Scaramuzza/OCam模型
- 使用模板摄像头配置生成新的配置文件

依赖:
    pip install pandas openpyxl pyyaml

所需库版本：
    - pandas >= 1.3.0
    - openpyxl >= 3.1.0
    - pyyaml >= 5.4.0
"""

import json
import yaml
import pandas as pd
import copy
import os
import argparse
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime


# 注册 OpenCV YAML 标签构造器(opencv-matrix)
def opencv_matrix_constructor(loader, node):
    """解析 OpenCV 矩阵标签为二维数组(list[list[float]])。

    YAML 示例:
      T_v_c: !!opencv-matrix
        rows: 4
        cols: 4
        dt: d
        data: [ ... ]
    """
    try:
        mapping = loader.construct_mapping(node, deep=True)
        rows = int(mapping.get("rows", 0))
        cols = int(mapping.get("cols", 0))
        data = mapping.get("data", [])
        if rows <= 0 or cols <= 0 or not isinstance(data, list) or len(data) != rows * cols:
            return None
        return [data[i * cols:(i + 1) * cols] for i in range(rows)]
    except Exception:
        return None

yaml.SafeLoader.add_constructor('tag:yaml.org,2002:opencv-matrix', opencv_matrix_constructor)


# ============================================================================
# 配置常量
# ============================================================================

# 模板摄像头名称
TEMPLATE_CAMERA_NAME = "side_view_camera_front_left"

# CameraType(Excel)到 camera_name(YAML/JSON)的映射表
CAMERA_TYPE_MAPPING = {
    "Front Tele": "side_view_camera_front_tele",
    "Front Wide": "side_view_camera_front_wide",
    "Wing Front Left": "side_view_camera_front_left",
    "Wing Front Right": "side_view_camera_front_right",
    "Wing Rear Left": "side_view_camera_rear_left",
    "Wing Rear Right": "side_view_camera_rear_right",
    "NRCS Front": "surround_view_camera_front",
    "NRCS Left": "surround_view_camera_left",
    "NRCS Right": "surround_view_camera_right",
    "NRCS Rear": "surround_view_camera_rear",
    "Rear": "side_view_camera_rear",
}


# ============================================================================
# 日志配置
# ============================================================================

def setup_logger(level: str = "INFO") -> logging.Logger:
    """配置并返回日志记录器"""
    logger = logging.getLogger("CameraConfigUpdater")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# ============================================================================
# 数据加载函数
# ============================================================================

def load_json_template(json_path: Path, logger: logging.Logger) -> Dict[str, Any]:
    """加载 JSON 模板文件"""
    logger.info(f"加载 JSON 模板: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'sensors' not in data:
        raise ValueError(f"JSON 文件缺少 'sensors' 字段: {json_path}")

    if TEMPLATE_CAMERA_NAME not in data['sensors']:
        raise ValueError(
            f"未找到模板摄像头 '{TEMPLATE_CAMERA_NAME}' 在 JSON 的 sensors 中"
        )

    logger.info(f"✓ 成功加载模板摄像头: {TEMPLATE_CAMERA_NAME}")
    return data


def load_excel_extrinsics(
    excel_path: Path,
    logger: logging.Logger
) -> pd.DataFrame:
    """
    加载 Excel 外参数据

    返回包含以下列的 DataFrame:
    - CameraType: 摄像头类型名称
    - x, y, z: 位置坐标(米)
    - roll, pitch, yaw: 旋转角度(度)
    """
    logger.info(f"加载 Excel 外参: {excel_path}")

    df = pd.read_excel(excel_path)

    # 标准化列名(处理 'pith' 拼写错误)
    df.columns = df.columns.str.strip()
    if 'pith' in df.columns and 'pitch' not in df.columns:
        df.rename(columns={'pith': 'pitch'}, inplace=True)
        logger.warning("已将列名 'pith' 修正为 'pitch'")

    # 验证必需列
    required_cols = ['CameraType', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Excel 文件缺少必需列: {missing_cols}\n"
            f"当前列: {list(df.columns)}"
        )

    # 过滤掉非摄像头行(NaN 或非映射表中的类型)
    df = df[df['CameraType'].notna()].copy()
    df = df[df['CameraType'].isin(CAMERA_TYPE_MAPPING.keys())].copy()

    logger.info(f"✓ 从 Excel 加载了 {len(df)} 个摄像头外参")
    return df


def load_yaml_intrinsics(
    yaml_dir: Path,
    logger: logging.Logger
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    加载 YAML 内参数据

    返回:
    - intrinsics_dict: {camera_name: {yaml数据}} 字典
    - warnings: 警告信息列表
    """
    logger.info(f"扫描 YAML 内参目录: {yaml_dir}")

    intrinsics_dict = {}
    warnings = []
    yaml_files = sorted(list(yaml_dir.glob("*.yaml")) + list(yaml_dir.glob("*.yml")))

    for yaml_path in yaml_files:
        try:
            # 读取并预处理 YAML 内容(处理非标准的 %YAML:1.0 指令)
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复非标准的 YAML 指令 %YAML:1.0 -> %YAML 1.0
            content = content.replace('%YAML:1.0', '%YAML 1.0')

            yaml_data = yaml.safe_load(content)

            if not isinstance(yaml_data, dict):
                warnings.append(f"跳过非字典 YAML: {yaml_path.name}")
                continue

            camera_name = yaml_data.get('camera_name')
            if not camera_name:
                logger.debug(f"跳过缺少 camera_name 的 YAML: {yaml_path.name}")
                continue

            # 检查模型类型(支持 PINHOLE 模型和 OCAM/SCARAMUZZA 模型)
            model_type = yaml_data.get('model_type', '').strip().upper()
            if model_type and model_type != 'PINHOLE' and model_type != 'SCARAMUZZA':
                warnings.append(
                    f"{camera_name}: 不支持的模型类型 '{model_type}' "
                    f"(仅支持 PINHOLE 和 SCARAMUZZA 模型) ({yaml_path.name})"
                )
                continue
            
            if model_type == 'PINHOLE':
                # 验证必需字段
                if 'projection_parameters' not in yaml_data:
                    warnings.append(f"{camera_name}: 缺少 projection_parameters ({yaml_path.name})")
                    continue

                proj = yaml_data['projection_parameters']
                required_proj = ['fx', 'fy', 'cx', 'cy']
                missing = [k for k in required_proj if k not in proj]

                if missing:
                    warnings.append(
                        f"{camera_name}: projection_parameters 缺少 {missing} ({yaml_path.name})"
                    )
                    continue

                # 检查畸变参数(可选, 缺失时会警告并补零)
                if 'distortion_parameters' not in yaml_data:
                    warnings.append(f"{camera_name}: 缺少 distortion_parameters, 将使用零值 ({yaml_path.name})")
                    yaml_data['distortion_parameters'] = {}
            
            elif model_type == 'SCARAMUZZA':
                # 验证必需字段
                if 'poly_parameters' not in yaml_data or 'inv_poly_parameters' not in yaml_data or 'affine_parameters' not in yaml_data:
                    warnings.append(f"{camera_name}: 缺少 poly_parameters, inv_poly_parameters, affine_parameters ({yaml_path.name})")
                    continue

                required_sections = ['poly_parameters', 'inv_poly_parameters', 'affine_parameters']
                missing = [k for k in required_sections if k not in yaml_data]
                if missing:
                    warnings.append(f"{camera_name}: SCARAMUZZA 模型缺少 {missing} ({yaml_path.name})")
                    continue
            
            else:
                warnings.append(
                    f"{camera_name}: 不支持的模型类型 '{model_type}' "
                    f"(仅支持 PINHOLE 和 SCARAMUZZA) ({yaml_path.name})"
                )
                continue

            # 检测重复
            if camera_name in intrinsics_dict:
                prev_path = intrinsics_dict[camera_name].get('_source_path', 'unknown')
                warnings.append(
                    f"{camera_name}: 重复的 YAML 文件 ({prev_path} 和 {yaml_path.name}), "
                    f"将使用后者"
                )

            yaml_data['_source_path'] = str(yaml_path)
            intrinsics_dict[camera_name] = yaml_data
            logger.debug(f"✓ 加载内参: {camera_name} <- {yaml_path.name}")

        except Exception as e:
            warnings.append(f"读取 YAML 失败 {yaml_path.name}: {e}")

    logger.info(f"✓ 加载了 {len(intrinsics_dict)} 个摄像头内参")
    return intrinsics_dict, warnings


# ============================================================================
# 数据处理函数
# ============================================================================

def extract_extrinsics_from_excel_row(row: pd.Series) -> Optional[Dict[str, Any]]:
    """
    从 Excel 行提取外参

    返回: {position: [x, y, z], rotation: {yaw, pitch, roll}}
    如果数据不完整或包含非有限值返回 None
    """
    try:
        x = float(row['x'])
        y = float(row['y'])
        z = float(row['z'])
        roll = float(row['roll'])
        pitch = float(row['pitch'])
        yaw = float(row['yaw'])

        # 检查是否为有限值(排除 NaN 和 Inf)
        values = [x, y, z, roll, pitch, yaw]
        if not all(math.isfinite(v) for v in values):
            return None
    
        return {
            'position': [x, y, z],
            'rotation': {
                'yaw': yaw,
                'pitch': pitch,
                'roll': roll
            }
        }
    except (ValueError, TypeError, KeyError) as e:
        return None


def extract_extrinsics_from_yaml(
    yaml_data: Dict[str, Any],
    matrix_key: str = "T_v_c"
) -> Dict[str, Any]:
    """从 YAML 中提取外参(当前仅支持 position)。

    约定:
    - 优先读取 OpenCV 矩阵 `T_v_c` 的平移项作为 position (单位: 米)
    - rotation 不从 YAML 推导(姿态角定义需与 aiSim yaw/pitch/roll 约定对齐，默认以 JSON 模板为准)
    """
    matrix = yaml_data.get(matrix_key)
    if (
        isinstance(matrix, list)
        and len(matrix) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in matrix)
    ):
        try:
            x = float(matrix[0][3])
            y = float(matrix[1][3])
            z = float(matrix[2][3])
            if all(math.isfinite(v) for v in [x, y, z]):
                return {"position": [x, y, z]}
        except Exception:
            pass
    return {}


def extract_intrinsics_from_yaml(
    yaml_data: Dict[str, Any],
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    从 YAML 数据提取内参

    返回字典包含:
    - aiSim的model_type: 'OpenCVPinhole' 或 'OcamFisheye'
    - 以及对应的内参字段
    """
    model_type_yaml = yaml_data.get('model_type', '').strip().upper()
    camera_name = yaml_data.get('camera_name', 'unknown')

    # --- SCARAMUZZA (OCam) 提取逻辑 ---
    if model_type_yaml == 'SCARAMUZZA':
        poly = yaml_data['poly_parameters']
        inv_poly = yaml_data['inv_poly_parameters']
        affine = yaml_data['affine_parameters']

        # 提取 p0-p4 用于 polynomial_coefficients
        poly_coeffs = [float(poly.get(f'p{i}', 0.0)) for i in range(5)]
        
        # 提取 p0-p15 用于 inv_polynomial_coefficients (只取前16个)
        inv_poly_coeffs = [float(inv_poly.get(f'p{i}', 0.0)) for i in range(16)]

        # 提取主点 (忽略 ac, ad, ae)
        cx = float(affine.get('cx', 0.0))
        cy = float(affine.get('cy', 0.0))

        return {
            'model_type': 'OcamFisheye',
            'principal_point': [cx, cy],
            'polynomial_coefficients': poly_coeffs,
            'inv_polynomial_coefficients': inv_poly_coeffs,
            'width': yaml_data.get('image_width'),
            'height': yaml_data.get('image_height')
        }

    # --- PINHOLE 提取逻辑 (默认) ---
    else:
        proj = yaml_data['projection_parameters']
        dist = yaml_data.get('distortion_parameters', {})

        camera_name = yaml_data.get('camera_name', 'unknown')

        # 检查缺失的畸变参数
        required_dist = ['k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'p1', 'p2']
        missing_dist = [k for k in required_dist if k not in dist]

        if missing_dist:
            logger.warning(
                f"{camera_name}: 畸变参数缺失 {missing_dist}, 将使用 0.0"
            )

        # 提取畸变参数(缺失时默认为 0.0)
        k1 = dist.get('k1', 0.0)
        k2 = dist.get('k2', 0.0)
        k3 = dist.get('k3', 0.0)
        k4 = dist.get('k4', 0.0)
        k5 = dist.get('k5', 0.0)
        k6 = dist.get('k6', 0.0)
        p1 = dist.get('p1', 0.0)
        p2 = dist.get('p2', 0.0)

        return {
            'model_type': 'OpenCVPinhole',
            'focal_length': [float(proj['fx']), float(proj['fy'])],
            'principal_point': [float(proj['cx']), float(proj['cy'])],
            'distortion_coefficients': [
                float(k1), float(k2), float(p1), float(p2), float(k3)
            ],
            'rational_model_coefficients': [
                float(k4), float(k5), float(k6)
            ],
            'width': yaml_data.get('image_width'),
            'height': yaml_data.get('image_height')
        }


def create_camera_config(
    template: Dict[str, Any],
    extrinsics: Dict[str, Any],
    intrinsics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    基于模板创建新的摄像头配置

    参数:
    - template: 模板摄像头配置(会深拷贝)
    - extrinsics: 外参 {position, rotation}
    - intrinsics: 内参 根据内参类型自动适配模型
    """
    camera_config = copy.deepcopy(template)

    # 更新外参
    camera_config['camera_config']['position'] = extrinsics['position']
    camera_config['camera_config']['rotation'] = extrinsics['rotation']

    # 更新内参
    target_model = intrinsics['model_type']
    camera_config['camera_config']['model'] = target_model
    
    # 获取 distortion_parameters 引用 (aiSim 中 OCam 参数也通常放在这里，或作为 config 的直接子项)
    # 基于 Pinhole 的 JSON 结构，内参都在 distortion_parameters 字典下
    dist_params = camera_config['camera_config']['distortion_parameters']
    
    if target_model == 'OcamFisheye':
        # --- OCam 配置 ---
        # 清除 Pinhole 专用字段
        dist_params.clear()
        
        # 填充 OCam 字段
        dist_params['principal_point'] = intrinsics['principal_point']
        dist_params['polynomial_coefficients'] = intrinsics['polynomial_coefficients']
        dist_params['inv_polynomial_coefficients'] = intrinsics['inv_polynomial_coefficients']

        # FOV 大于120 启用 Cube_6_Face 映射
        camera_config['camera_config']['render_properties']['environment_mapping_type'] = 'Cube_6_Face'
        
        # 如果 YAML 中指定了分辨率，也一并更新 (可选)
        if intrinsics.get('width') and intrinsics.get('height'):
            camera_config['camera_config']['width'] = intrinsics['width']
            camera_config['camera_config']['height'] = intrinsics['height']

    else:
        # --- Pinhole 配置 ---
        dist_params['focal_length'] = intrinsics['focal_length']
        dist_params['principal_point'] = intrinsics['principal_point']
        dist_params['distortion_coefficients'] = intrinsics['distortion_coefficients']
        dist_params['rational_model_coefficients'] = intrinsics['rational_model_coefficients']
        if intrinsics.get('width') and intrinsics.get('height'):
            camera_config['camera_config']['width'] = intrinsics['width']
            camera_config['camera_config']['height'] = intrinsics['height']

    return camera_config


# ============================================================================
# 主处理逻辑
# ============================================================================

def build_extrinsics(
    base_sensor: Dict[str, Any],
    excel_extrinsics: Optional[Dict[str, Any]],
    yaml_extrinsics: Dict[str, Any],
    position_source: str,
    rotation_source: str,
) -> Dict[str, Any]:
    """根据来源策略合成最终外参。

    position_source: template|excel|yaml
    rotation_source: template|excel
    """
    base_camera_config = base_sensor.get("camera_config", {})
    base_position = base_camera_config.get("position")
    base_rotation = base_camera_config.get("rotation")

    if not isinstance(base_position, list) or len(base_position) != 3:
        base_position = None
    if not isinstance(base_rotation, dict):
        base_rotation = None

    position = base_position
    if position_source == "excel":
        if not excel_extrinsics or "position" not in excel_extrinsics:
            raise ValueError("position_source=excel 但缺少 Excel 外参")
        position = excel_extrinsics["position"]
    elif position_source == "yaml":
        position = yaml_extrinsics.get("position", base_position)

    rotation = base_rotation
    if rotation_source == "excel":
        if not excel_extrinsics or "rotation" not in excel_extrinsics:
            raise ValueError("rotation_source=excel 但缺少 Excel 外参")
        rotation = excel_extrinsics["rotation"]

    if position is None or rotation is None:
        raise ValueError("无法构建完整外参(请检查模板 JSON 是否包含 position/rotation)")

    return {"position": position, "rotation": rotation}


def process_cameras(
    template_data: Dict[str, Any],
    extrinsics_df: pd.DataFrame,
    intrinsics_dict: Dict[str, Dict[str, Any]],
    logger: logging.Logger,
    position_source: str,
    rotation_source: str
) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """
    处理所有摄像头并生成更新后的配置

    返回:
    - updated_data: 更新后的完整 JSON 数据
    - report: 报告字典 {success: [...], skipped: [...], errors: [...]}
    """
    updated_data = copy.deepcopy(template_data)
    template_sensor = updated_data['sensors'][TEMPLATE_CAMERA_NAME]

    report = {
        'success': [],
        'skipped': [],
        'errors': []
    }

    for idx, row in extrinsics_df.iterrows():
        camera_type = row['CameraType']
        camera_name = CAMERA_TYPE_MAPPING.get(camera_type)

        if not camera_name:
            logger.debug(f"跳过未映射的 CameraType: {camera_type}")
            continue

        # 提取外参
        extrinsics = extract_extrinsics_from_excel_row(row)
        if extrinsics is None:
            msg = f"外参数据不完整(Excel 行 {idx})"
            logger.warning(f"⚠ {camera_name}: {msg}")
            report['skipped'].append(f"{camera_name} - {msg}")
            continue

        # 获取内参
        if camera_name not in intrinsics_dict:
            msg = "未找到对应的 YAML 内参文件"
            logger.warning(f"⚠ {camera_name}: {msg}")
            report['skipped'].append(f"{camera_name} - {msg}")
            continue

        try:
            base_sensor = updated_data['sensors'].get(camera_name, template_sensor)
            yaml_data = intrinsics_dict[camera_name]
            intrinsics = extract_intrinsics_from_yaml(yaml_data, logger)
            yaml_extrinsics = extract_extrinsics_from_yaml(yaml_data)
            merged_extrinsics = build_extrinsics(
                base_sensor=base_sensor,
                excel_extrinsics=extrinsics,
                yaml_extrinsics=yaml_extrinsics,
                position_source=position_source,
                rotation_source=rotation_source,
            )

            # 创建新的摄像头配置
            new_config = create_camera_config(base_sensor, merged_extrinsics, intrinsics)
            updated_data['sensors'][camera_name] = new_config

            yaml_file = Path(yaml_data['_source_path']).name
            logger.info(f"✓ 成功更新: {camera_name} (YAML: {yaml_file})")
            report['success'].append(camera_name)

        except Exception as e:
            msg = f"处理时发生异常: {e}"
            logger.error(f"✗ {camera_name}: {msg}")
            report['errors'].append(f"{camera_name} - {msg}")

    return updated_data, report


def process_cameras_from_yaml(
    template_data: Dict[str, Any],
    intrinsics_dict: Dict[str, Dict[str, Any]],
    logger: logging.Logger,
    position_source: str,
) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """仅基于 YAML 列表更新摄像头配置。

    - camera_name 来自 YAML
    - 默认外参以模板 JSON 为准；如 position_source=yaml 则使用 YAML 的 T_v_c 平移覆盖 position
    """
    updated_data = copy.deepcopy(template_data)
    template_sensor = updated_data["sensors"][TEMPLATE_CAMERA_NAME]

    report = {
        "success": [],
        "skipped": [],
        "errors": [],
    }

    for camera_name, yaml_data in intrinsics_dict.items():
        try:
            base_sensor = updated_data["sensors"].get(camera_name, template_sensor)
            intrinsics = extract_intrinsics_from_yaml(yaml_data, logger)
            yaml_extrinsics = extract_extrinsics_from_yaml(yaml_data)
            merged_extrinsics = build_extrinsics(
                base_sensor=base_sensor,
                excel_extrinsics=None,
                yaml_extrinsics=yaml_extrinsics,
                position_source=position_source,
                rotation_source="template",
            )

            new_config = create_camera_config(base_sensor, merged_extrinsics, intrinsics)
            updated_data["sensors"][camera_name] = new_config

            yaml_file = Path(yaml_data["_source_path"]).name
            logger.info(f"✓ 成功更新: {camera_name} (YAML: {yaml_file})")
            report["success"].append(camera_name)
        except Exception as e:
            msg = f"处理时发生异常: {e}"
            logger.error(f"✗ {camera_name}: {msg}")
            report["errors"].append(f"{camera_name} - {msg}")

    return updated_data, report


def save_json(
    data: Dict[str, Any],
    output_path: Path,
    backup_original: bool,
    logger: logging.Logger
) -> None:
    """保存 JSON 文件(支持备份)"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_original and output_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = output_path.with_name(f"{output_path.stem}_backup_{timestamp}.json")
        import shutil
        shutil.copy2(output_path, backup_path)
        logger.info(f"✓ 已备份原文件: {backup_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

    logger.info(f"✓ 已保存更新后的配置: {output_path}")


def print_report(report: Dict[str, List[str]], logger: logging.Logger) -> None:
    """打印处理报告"""
    logger.info("\n" + "="*60)
    logger.info("处理报告")
    logger.info("="*60)

    logger.info(f"\n✓ 成功: {len(report['success'])} 个摄像头")
    for name in report['success']:
        logger.info(f"  - {name}")

    if report['skipped']:
        logger.info(f"\n⚠ 跳过: {len(report['skipped'])} 个摄像头")
        for msg in report['skipped']:
            logger.info(f"  - {msg}")

    if report['errors']:
        logger.info(f"\n✗ 失败: {len(report['errors'])} 个摄像头")
        for msg in report['errors']:
            logger.info(f"  - {msg}")

    logger.info("\n" + "="*60)


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="批量更新 aiSim 摄像头配置文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认模式(生成新文件)
  python update_camera_config.py

  # 覆盖原文件(会自动备份)
  python update_camera_config.py --in-place

  # 仅测试不写入文件
  python update_camera_config.py --dry-run

  # 调试模式
  python update_camera_config.py --log-level DEBUG
        """
    )

    parser.add_argument(
        '--json',
        type=Path,
        default=Path('camera-converter/templates/Bosch_Camera_RGBA.json'),
        help='JSON 模板文件路径 (默认: camera-converter/templates/Bosch_Camera_RGBA.json)'
    )

    parser.add_argument(
        '--excel',
        type=Path,
        default=Path('input/整车传感器参数.xlsx'),
        help='Excel 外参文件路径 (默认: input/整车传感器参数.xlsx)'
    )

    parser.add_argument(
        '--yaml-dir',
        type=Path,
        default=Path('input/Camera/标定参数'),
        help='YAML 内参目录路径 (默认: input/Camera/标定参数)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='输出 JSON 文件路径 (默认: 在模板文件名后加 _updated)'
    )

    parser.add_argument(
        '--in-place',
        action='store_true',
        help='覆盖原 JSON 文件(会自动创建备份)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅测试, 不实际写入文件'
    )

    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )

    parser.add_argument(
        '--camera-source',
        default='yaml',
        choices=['excel', 'yaml'],
        help='摄像头列表来源 (默认: yaml; 选 excel 则按 Excel 中的 CameraType 逐个更新)'
    )

    parser.add_argument(
        '--position-source',
        default='template',
        choices=['template', 'excel', 'yaml'],
        help='position 外参来源 (默认: template; 选 excel 则使用 Excel 的 x/y/z; 选 yaml 则读取 YAML 的 T_v_c 平移)'
    )

    parser.add_argument(
        '--rotation-source',
        default='template',
        choices=['template', 'excel'],
        help='rotation 外参来源 (默认: template; 选 excel 则使用 Excel 的 roll/pitch/yaw，需确认欧拉角定义一致)'
    )

    args = parser.parse_args()
    logger = setup_logger(args.log_level)

    try:
        # 加载数据
        logger.info("开始批量更新摄像头配置\n")

        template_data = load_json_template(args.json, logger)
        intrinsics_dict, yaml_warnings = load_yaml_intrinsics(args.yaml_dir, logger)

        # 打印 YAML 加载警告
        if yaml_warnings:
            logger.info("\nYAML 加载警告:")
            for warning in yaml_warnings:
                logger.warning(f"  {warning}")

        logger.info("\n" + "-"*60)
        logger.info("开始处理摄像头配置...")
        logger.info("-"*60 + "\n")

        # 处理摄像头
        if args.camera_source == 'yaml':
            if args.position_source == 'excel' or args.rotation_source == 'excel':
                raise ValueError("camera_source=yaml 时不支持 position_source/rotation_source=excel")
            updated_data, report = process_cameras_from_yaml(
                template_data,
                intrinsics_dict,
                logger,
                position_source=args.position_source,
            )
        else:
            extrinsics_df = load_excel_extrinsics(args.excel, logger)
            updated_data, report = process_cameras(
                template_data,
                extrinsics_df,
                intrinsics_dict,
                logger,
                position_source=args.position_source,
                rotation_source=args.rotation_source,
            )

        # 打印报告
        print_report(report, logger)

        # 保存文件
        if not args.dry_run:
            if args.in_place:
                output_path = args.json
                backup = True
            elif args.output:
                output_path = args.output
                backup = False
            else:
                # 默认: 添加 _updated 后缀
                output_path = args.json.with_name(
                    f"{args.json.stem}_updated{args.json.suffix}"
                )
                backup = False

            save_json(updated_data, output_path, backup, logger)
        else:
            logger.info("\n[DRY-RUN] 未写入任何文件")

        # 返回退出码
        return 0 if not report['errors'] else 1

    except Exception as e:
        logger.error(f"\n✗ 发生错误: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
