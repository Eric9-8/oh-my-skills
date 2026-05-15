#!/usr/bin/env python3
"""
验证 aiSim Camera 配置与原始 YAML 标定参数的一致性

功能：
- 对比生成的 JSON 配置与原始 YAML 内参
- 检查模型类型、分辨率、畸变系数等关键参数
- 生成验证报告（Markdown 格式）

依赖：
    pip install pyyaml

用法：
    python validate_camera_config.py \
        --json output/Camera/Bosch_Camera_RGBA_generated.json \
        --yaml-dir input/Camera/标定参数 \
        --out output/Camera/validation_report.md
"""

import json
import yaml
import argparse
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime


# 注册 OpenCV YAML 标签构造器
def opencv_matrix_constructor(loader, node):
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


def load_yaml_files(yaml_dir: Path) -> Dict[str, Dict[str, Any]]:
    """加载目录下所有 YAML 标定文件"""
    yaml_dict = {}
    for yaml_path in sorted(yaml_dir.glob("*.yaml")):
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = f.read().replace('%YAML:1.0', '%YAML 1.0')
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'camera_name' in data:
                data['_source_file'] = yaml_path.name
                yaml_dict[data['camera_name']] = data
        except Exception as e:
            print(f"警告: 无法加载 {yaml_path.name}: {e}")
    return yaml_dict


def load_json_config(json_path: Path) -> Dict[str, Any]:
    """加载 JSON 配置文件"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_floats(a: float, b: float, rel_tol: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    """比较两个浮点数是否相等"""
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def compare_arrays(arr1: List[float], arr2: List[float], rel_tol: float = 1e-6) -> Tuple[bool, float]:
    """比较两个数组，返回是否匹配和最大相对误差"""
    if len(arr1) != len(arr2):
        return False, float('inf')
    max_rel_err = 0.0
    for a, b in zip(arr1, arr2):
        if a == 0 and b == 0:
            continue
        if a == 0 or b == 0:
            max_rel_err = max(max_rel_err, abs(a - b))
        else:
            rel_err = abs(a - b) / max(abs(a), abs(b))
            max_rel_err = max(max_rel_err, rel_err)
    return max_rel_err <= rel_tol, max_rel_err


def validate_pinhole(yaml_data: Dict, json_dist: Dict) -> Dict[str, Any]:
    """验证 Pinhole 模型参数"""
    results = {'model': 'OpenCVPinhole', 'checks': [], 'passed': True}

    proj = yaml_data.get('projection_parameters', {})
    dist = yaml_data.get('distortion_parameters', {})

    # 检查焦距
    yaml_focal = [proj.get('fx', 0), proj.get('fy', 0)]
    json_focal = json_dist.get('focal_length', [0, 0])
    match, err = compare_arrays(yaml_focal, json_focal)
    results['checks'].append({
        'name': 'focal_length',
        'yaml': yaml_focal,
        'json': json_focal,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    # 检查主点
    yaml_pp = [proj.get('cx', 0), proj.get('cy', 0)]
    json_pp = json_dist.get('principal_point', [0, 0])
    match, err = compare_arrays(yaml_pp, json_pp)
    results['checks'].append({
        'name': 'principal_point',
        'yaml': yaml_pp,
        'json': json_pp,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    # 检查畸变系数 [k1, k2, p1, p2, k3]
    yaml_distort = [
        dist.get('k1', 0), dist.get('k2', 0),
        dist.get('p1', 0), dist.get('p2', 0),
        dist.get('k3', 0)
    ]
    json_distort = json_dist.get('distortion_coefficients', [0]*5)
    match, err = compare_arrays(yaml_distort, json_distort)
    results['checks'].append({
        'name': 'distortion_coefficients',
        'yaml': yaml_distort,
        'json': json_distort,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    # 检查 rational_model_coefficients [k4, k5, k6]
    yaml_rational = [dist.get('k4', 0), dist.get('k5', 0), dist.get('k6', 0)]
    json_rational = json_dist.get('rational_model_coefficients', [0]*3)
    match, err = compare_arrays(yaml_rational, json_rational)
    results['checks'].append({
        'name': 'rational_model_coefficients',
        'yaml': yaml_rational,
        'json': json_rational,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    return results


def validate_ocam(yaml_data: Dict, json_dist: Dict) -> Dict[str, Any]:
    """验证 OcamFisheye 模型参数"""
    results = {'model': 'OcamFisheye', 'checks': [], 'passed': True}

    poly = yaml_data.get('poly_parameters', {})
    inv_poly = yaml_data.get('inv_poly_parameters', {})
    affine = yaml_data.get('affine_parameters', {})

    # 检查主点
    yaml_pp = [affine.get('cx', 0), affine.get('cy', 0)]
    json_pp = json_dist.get('principal_point', [0, 0])
    match, err = compare_arrays(yaml_pp, json_pp)
    results['checks'].append({
        'name': 'principal_point',
        'yaml': yaml_pp,
        'json': json_pp,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    # 检查 polynomial_coefficients (p0-p4)
    yaml_poly = [poly.get(f'p{i}', 0) for i in range(5)]
    json_poly = json_dist.get('polynomial_coefficients', [0]*5)
    match, err = compare_arrays(yaml_poly, json_poly)
    results['checks'].append({
        'name': 'polynomial_coefficients',
        'yaml': yaml_poly,
        'json': json_poly,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    # 检查 inv_polynomial_coefficients (p0-p15)
    yaml_inv = [inv_poly.get(f'p{i}', 0) for i in range(16)]
    json_inv = json_dist.get('inv_polynomial_coefficients', [0]*16)
    match, err = compare_arrays(yaml_inv, json_inv)
    results['checks'].append({
        'name': 'inv_polynomial_coefficients',
        'yaml': yaml_inv,
        'json': json_inv,
        'match': match,
        'max_rel_err': err
    })
    if not match:
        results['passed'] = False

    return results


def validate_camera(camera_name: str, yaml_data: Dict, json_sensor: Dict) -> Dict[str, Any]:
    """验证单个相机配置"""
    result = {
        'camera_name': camera_name,
        'yaml_file': yaml_data.get('_source_file', 'unknown'),
        'checks': {},
        'passed': True
    }

    json_config = json_sensor.get('camera_config', {})
    json_dist = json_config.get('distortion_parameters', {})

    # 检查模型类型
    yaml_model = yaml_data.get('model_type', '').upper()
    json_model = json_config.get('model', '')

    expected_model = 'OpenCVPinhole' if yaml_model == 'PINHOLE' else 'OcamFisheye'
    model_match = json_model == expected_model
    result['checks']['model_type'] = {
        'yaml': yaml_model,
        'json': json_model,
        'expected': expected_model,
        'match': model_match
    }
    if not model_match:
        result['passed'] = False

    # 检查分辨率
    yaml_width = yaml_data.get('image_width')
    yaml_height = yaml_data.get('image_height')
    json_width = json_config.get('width')
    json_height = json_config.get('height')

    res_match = (yaml_width == json_width and yaml_height == json_height)
    result['checks']['resolution'] = {
        'yaml': f"{yaml_width}x{yaml_height}",
        'json': f"{json_width}x{json_height}",
        'match': res_match
    }
    if not res_match:
        result['passed'] = False

    # 检查内参
    if yaml_model == 'PINHOLE':
        intrinsic_result = validate_pinhole(yaml_data, json_dist)
    else:
        intrinsic_result = validate_ocam(yaml_data, json_dist)

    result['checks']['intrinsics'] = intrinsic_result
    if not intrinsic_result['passed']:
        result['passed'] = False

    # 检查 OcamFisheye 的 environment_mapping_type
    if json_model == 'OcamFisheye':
        env_type = json_config.get('render_properties', {}).get('environment_mapping_type')
        env_match = env_type == 'Cube_6_Face'
        result['checks']['environment_mapping'] = {
            'json': env_type,
            'expected': 'Cube_6_Face',
            'match': env_match
        }
        if not env_match:
            result['passed'] = False

    return result


def generate_report(results: List[Dict], output_path: Path) -> str:
    """生成 Markdown 验证报告"""
    lines = [
        "# Camera Config 验证报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总览",
        "",
    ]

    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    lines.append(f"- 验证相机数: **{total}**")
    lines.append(f"- 通过: **{passed}** / {total}")
    lines.append(f"- 失败: **{total - passed}** / {total}")
    lines.append("")

    # 汇总表格
    lines.append("## 验证结果汇总")
    lines.append("")
    lines.append("| 相机名称 | YAML 文件 | 模型 | 分辨率 | 内参 | 状态 |")
    lines.append("|---------|----------|------|--------|------|------|")

    for r in results:
        status = "✅" if r['passed'] else "❌"
        model_check = r['checks'].get('model_type', {})
        res_check = r['checks'].get('resolution', {})
        intrinsic_check = r['checks'].get('intrinsics', {})

        model_status = "✅" if model_check.get('match') else "❌"
        res_status = "✅" if res_check.get('match') else "❌"
        intrinsic_status = "✅" if intrinsic_check.get('passed') else "❌"

        lines.append(f"| {r['camera_name']} | {r['yaml_file']} | {model_status} | {res_status} | {intrinsic_status} | {status} |")

    lines.append("")

    # 详细结果（仅显示失败项）
    failed_results = [r for r in results if not r['passed']]
    if failed_results:
        lines.append("## 失败详情")
        lines.append("")

        for r in failed_results:
            lines.append(f"### {r['camera_name']}")
            lines.append("")

            for check_name, check_data in r['checks'].items():
                if check_name == 'intrinsics':
                    if not check_data.get('passed'):
                        lines.append(f"**内参验证失败** ({check_data.get('model')}):")
                        lines.append("")
                        for c in check_data.get('checks', []):
                            if not c.get('match'):
                                lines.append(f"- `{c['name']}`:")
                                lines.append(f"  - YAML: `{c['yaml']}`")
                                lines.append(f"  - JSON: `{c['json']}`")
                                lines.append(f"  - 最大相对误差: `{c.get('max_rel_err', 'N/A')}`")
                        lines.append("")
                elif not check_data.get('match'):
                    lines.append(f"**{check_name}**: YAML=`{check_data.get('yaml')}`, JSON=`{check_data.get('json')}`")
                    lines.append("")

    # 写入文件
    report_content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_content


def main():
    parser = argparse.ArgumentParser(description="验证 aiSim Camera 配置与原始 YAML 的一致性")
    parser.add_argument('--json', type=Path, required=True, help='生成的 JSON 配置文件')
    parser.add_argument('--yaml-dir', type=Path, required=True, help='YAML 标定参数目录')
    parser.add_argument('--out', type=Path, default=None, help='输出报告路径 (默认: 打印到终端)')
    args = parser.parse_args()

    # 加载数据
    yaml_dict = load_yaml_files(args.yaml_dir)
    json_data = load_json_config(args.json)
    json_sensors = json_data.get('sensors', {})

    print(f"加载了 {len(yaml_dict)} 个 YAML 文件")
    print(f"JSON 中有 {len(json_sensors)} 个相机配置")
    print()

    # 验证每个相机
    results = []
    for camera_name, yaml_data in yaml_dict.items():
        if camera_name in json_sensors:
            result = validate_camera(camera_name, yaml_data, json_sensors[camera_name])
            results.append(result)
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} {camera_name}")
        else:
            print(f"⚠️  SKIP {camera_name} (JSON 中不存在)")

    # 生成报告
    print()
    if args.out:
        report = generate_report(results, args.out)
        print(f"报告已保存到: {args.out}")
    else:
        passed = sum(1 for r in results if r['passed'])
        print(f"验证完成: {passed}/{len(results)} 通过")

    # 返回退出码
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
