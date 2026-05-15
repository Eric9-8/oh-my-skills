#!/usr/bin/env python3
"""
验证 aiSim Camera 图像畸变效果

功能：
- 读取导出的 TGA/PNG 图像
- 检测棋盘格线条（使用边缘检测和霍夫变换）
- 分析线条直线度（畸变会导致直线变弯）
- 生成验证报告

依赖：
    pip install opencv-python numpy pillow

用法：
    python validate_camera_distortion.py \
        --image-dir output/Camera/export/ \
        --config output/Camera/Bosch_Camera_RGBA_updated.json \
        --out output/Camera/distortion_report.md
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("警告: opencv-python 未安装，部分功能不可用")
    print("安装: pip install opencv-python numpy")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load_tga_image(image_path: Path) -> Optional[np.ndarray]:
    """加载 TGA 图像"""
    if not HAS_CV2:
        return None

    # OpenCV 可以直接读取 TGA
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None and HAS_PIL:
        # 尝试用 PIL 读取
        try:
            pil_img = Image.open(image_path)
            img = np.array(pil_img.convert('RGB'))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except Exception:
            pass
    return img


def detect_lines(img: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
    """检测图像中的直线"""
    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 边缘检测
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # 霍夫变换检测直线
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=100,
        minLineLength=50,
        maxLineGap=10
    )

    return lines if lines is not None else [], edges


def calculate_line_straightness(lines: List[np.ndarray]) -> Dict[str, Any]:
    """计算线条直线度统计"""
    if len(lines) == 0:
        return {
            'line_count': 0,
            'avg_length': 0,
            'horizontal_count': 0,
            'vertical_count': 0,
            'diagonal_count': 0
        }

    lengths = []
    angles = []
    horizontal = 0
    vertical = 0
    diagonal = 0

    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        lengths.append(length)

        # 计算角度
        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan((y2-y1)/(x2-x1))))
        angles.append(angle)

        # 分类
        if angle < 15:
            horizontal += 1
        elif angle > 75:
            vertical += 1
        else:
            diagonal += 1

    return {
        'line_count': len(lines),
        'avg_length': np.mean(lengths),
        'max_length': np.max(lengths),
        'min_length': np.min(lengths),
        'horizontal_count': horizontal,
        'vertical_count': vertical,
        'diagonal_count': diagonal,
        'avg_angle': np.mean(angles)
    }


def detect_checkerboard_corners(img: np.ndarray) -> Tuple[bool, Optional[np.ndarray], int]:
    """尝试检测棋盘格角点"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 尝试不同的棋盘格尺寸
    board_sizes = [(9, 6), (8, 6), (7, 5), (6, 4), (5, 4)]

    for size in board_sizes:
        ret, corners = cv2.findChessboardCorners(
            gray, size,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
        )
        if ret:
            # 亚像素精度
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            return True, corners, size[0] * size[1]

    return False, None, 0


def analyze_corner_straightness(corners: np.ndarray, board_width: int) -> Dict[str, float]:
    """分析角点排列的直线度（检测畸变）"""
    if corners is None or len(corners) < 4:
        return {'row_straightness': 0, 'col_straightness': 0}

    corners = corners.reshape(-1, 2)
    n_corners = len(corners)
    board_height = n_corners // board_width

    row_errors = []
    col_errors = []

    # 检查每行的直线度
    for row in range(board_height):
        row_corners = corners[row * board_width:(row + 1) * board_width]
        if len(row_corners) >= 3:
            # 拟合直线
            vx, vy, x0, y0 = cv2.fitLine(row_corners.astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01)
            # 计算点到直线的距离
            for pt in row_corners:
                dist = abs((pt[1] - y0) * vx - (pt[0] - x0) * vy) / np.sqrt(vx**2 + vy**2)
                row_errors.append(dist[0])

    # 检查每列的直线度
    for col in range(board_width):
        col_corners = corners[col::board_width]
        if len(col_corners) >= 3:
            vx, vy, x0, y0 = cv2.fitLine(col_corners.astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01)
            for pt in col_corners:
                dist = abs((pt[1] - y0) * vx - (pt[0] - x0) * vy) / np.sqrt(vx**2 + vy**2)
                col_errors.append(dist[0])

    return {
        'row_straightness': np.mean(row_errors) if row_errors else 0,
        'col_straightness': np.mean(col_errors) if col_errors else 0,
        'max_row_error': np.max(row_errors) if row_errors else 0,
        'max_col_error': np.max(col_errors) if col_errors else 0
    }


def analyze_image(image_path: Path) -> Dict[str, Any]:
    """分析单张图像"""
    result = {
        'file': image_path.name,
        'status': 'unknown',
        'resolution': None,
        'lines': None,
        'checkerboard': None,
        'straightness': None
    }

    if not HAS_CV2:
        result['status'] = 'error'
        result['error'] = 'opencv-python not installed'
        return result

    img = load_tga_image(image_path)
    if img is None:
        result['status'] = 'error'
        result['error'] = 'Failed to load image'
        return result

    result['resolution'] = f"{img.shape[1]}x{img.shape[0]}"

    # 检测直线
    lines, edges = detect_lines(img)
    result['lines'] = calculate_line_straightness(lines)

    # 检测棋盘格
    found, corners, n_corners = detect_checkerboard_corners(img)
    result['checkerboard'] = {
        'found': found,
        'corner_count': n_corners
    }

    # 如果找到棋盘格，分析直线度
    if found and corners is not None:
        board_width = 9  # 假设标准棋盘格
        result['straightness'] = analyze_corner_straightness(corners, board_width)
        result['status'] = 'pass' if result['straightness']['row_straightness'] < 2.0 else 'warning'
    elif result['lines']['line_count'] > 10:
        result['status'] = 'partial'  # 检测到线条但没有完整棋盘格
    else:
        result['status'] = 'no_pattern'

    return result


def find_camera_images(image_dir: Path) -> Dict[str, List[Path]]:
    """按相机名称分组图像文件"""
    camera_images = {}

    # 支持的图像格式
    patterns = ['*.tga', '*.TGA', '*.png', '*.PNG', '*.jpg', '*.JPG']

    for pattern in patterns:
        for img_path in image_dir.rglob(pattern):
            # 从目录结构提取相机名称
            # 结构: ego/<camera_name>/color/<camera_name>_<step>.tga
            # 或: <camera_name>_<step>_color.tga

            # 尝试从父目录的父目录获取相机名称
            if img_path.parent.name == 'color':
                camera_name = img_path.parent.parent.name
            else:
                # 从文件名提取
                name = img_path.stem
                # 格式: camera_name_00005_color 或 camera_name_00005
                match = re.match(r'(.+?)_\d{5}(?:_color)?$', name)
                if match:
                    camera_name = match.group(1)
                else:
                    camera_name = name.split('_')[0] if '_' in name else 'unknown'

            if camera_name not in camera_images:
                camera_images[camera_name] = []
            camera_images[camera_name].append(img_path)

    # 排序
    for camera_name in camera_images:
        camera_images[camera_name].sort()

    return camera_images


def load_camera_config(config_path: Path) -> Dict[str, Any]:
    """加载相机配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_report(
    results: Dict[str, List[Dict]],
    config: Dict[str, Any],
    output_path: Path
) -> str:
    """生成验证报告"""
    lines = [
        "# Camera 畸变验证报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总览",
        "",
    ]

    # 统计
    total_cameras = len(results)
    pass_count = 0
    partial_count = 0
    fail_count = 0

    for camera_name, analyses in results.items():
        if any(a['status'] == 'pass' for a in analyses):
            pass_count += 1
        elif any(a['status'] == 'partial' for a in analyses):
            partial_count += 1
        else:
            fail_count += 1

    lines.append(f"- 相机数量: **{total_cameras}**")
    lines.append(f"- 检测到完整棋盘格: **{pass_count}**")
    lines.append(f"- 检测到部分线条: **{partial_count}**")
    lines.append(f"- 未检测到有效图案: **{fail_count}**")
    lines.append("")

    # 汇总表格
    lines.append("## 验证结果汇总")
    lines.append("")
    lines.append("| 相机名称 | 模型 | 分辨率 | 检测线条数 | 棋盘格 | 直线度误差 | 状态 |")
    lines.append("|---------|------|--------|-----------|--------|-----------|------|")

    sensors = config.get('sensors', {})

    for camera_name, analyses in sorted(results.items()):
        # 取第一帧的分析结果
        analysis = analyses[0] if analyses else {}

        # 从配置获取模型类型
        sensor_config = sensors.get(camera_name, {}).get('camera_config', {})
        model = sensor_config.get('model', 'unknown')

        resolution = analysis.get('resolution', 'N/A')
        line_count = analysis.get('lines', {}).get('line_count', 0)

        checkerboard = analysis.get('checkerboard', {})
        cb_status = "✅" if checkerboard.get('found') else "❌"

        straightness = analysis.get('straightness', {})
        if straightness:
            error = f"{straightness.get('row_straightness', 0):.2f}px"
        else:
            error = "N/A"

        status_map = {
            'pass': '✅ 通过',
            'partial': '⚠️ 部分',
            'no_pattern': '❌ 无图案',
            'error': '❌ 错误',
            'unknown': '❓ 未知'
        }
        status = status_map.get(analysis.get('status', 'unknown'), '❓')

        lines.append(f"| {camera_name} | {model} | {resolution} | {line_count} | {cb_status} | {error} | {status} |")

    lines.append("")

    # 详细结果
    lines.append("## 详细分析")
    lines.append("")

    for camera_name, analyses in sorted(results.items()):
        lines.append(f"### {camera_name}")
        lines.append("")

        sensor_config = sensors.get(camera_name, {}).get('camera_config', {})
        model = sensor_config.get('model', 'unknown')

        lines.append(f"- 模型类型: `{model}`")

        if analyses:
            analysis = analyses[0]
            lines.append(f"- 分辨率: `{analysis.get('resolution', 'N/A')}`")
            lines.append(f"- 分析图像数: `{len(analyses)}`")

            line_stats = analysis.get('lines', {})
            if line_stats:
                lines.append(f"- 检测线条数: `{line_stats.get('line_count', 0)}`")
                lines.append(f"  - 水平线: `{line_stats.get('horizontal_count', 0)}`")
                lines.append(f"  - 垂直线: `{line_stats.get('vertical_count', 0)}`")
                lines.append(f"  - 斜线: `{line_stats.get('diagonal_count', 0)}`")

            checkerboard = analysis.get('checkerboard', {})
            if checkerboard.get('found'):
                lines.append(f"- 棋盘格角点: `{checkerboard.get('corner_count', 0)}`")

                straightness = analysis.get('straightness', {})
                if straightness:
                    lines.append(f"- 行直线度误差: `{straightness.get('row_straightness', 0):.3f}px`")
                    lines.append(f"- 列直线度误差: `{straightness.get('col_straightness', 0):.3f}px`")
                    lines.append(f"- 最大行误差: `{straightness.get('max_row_error', 0):.3f}px`")
                    lines.append(f"- 最大列误差: `{straightness.get('max_col_error', 0):.3f}px`")
            else:
                lines.append("- 棋盘格: 未检测到完整棋盘格")

        lines.append("")

    # 说明
    lines.append("## 说明")
    lines.append("")
    lines.append("- **直线度误差**: 角点到拟合直线的平均距离（像素），越小越好")
    lines.append("- **通过标准**: 直线度误差 < 2.0 像素")
    lines.append("- **部分检测**: 检测到线条但未找到完整棋盘格（可能是视角问题）")
    lines.append("")

    report_content = "\n".join(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_content


def main():
    parser = argparse.ArgumentParser(description="验证 aiSim Camera 图像畸变效果")
    parser.add_argument('--image-dir', type=Path, required=True, help='导出图像目录')
    parser.add_argument('--config', type=Path, required=True, help='相机配置 JSON 文件')
    parser.add_argument('--out', type=Path, default=None, help='输出报告路径')
    args = parser.parse_args()

    if not HAS_CV2:
        print("错误: 需要安装 opencv-python")
        print("运行: pip install opencv-python numpy")
        return 1

    # 查找图像文件
    print(f"扫描图像目录: {args.image_dir}")
    camera_images = find_camera_images(args.image_dir)

    if not camera_images:
        print("未找到图像文件")
        return 1

    print(f"找到 {len(camera_images)} 个相机的图像")

    # 加载配置
    config = load_camera_config(args.config)

    # 分析每个相机的图像
    results = {}
    for camera_name, images in camera_images.items():
        print(f"\n分析 {camera_name} ({len(images)} 张图像)...")
        results[camera_name] = []

        # 只分析前几帧
        for img_path in images[:3]:
            analysis = analyze_image(img_path)
            results[camera_name].append(analysis)

            status = analysis.get('status', 'unknown')
            line_count = analysis.get('lines', {}).get('line_count', 0)
            print(f"  {img_path.name}: {status}, {line_count} 条线")

    # 生成报告
    if args.out:
        report = generate_report(results, config, args.out)
        print(f"\n报告已保存到: {args.out}")
    else:
        # 打印简要结果
        print("\n" + "=" * 50)
        print("验证结果汇总")
        print("=" * 50)
        for camera_name, analyses in sorted(results.items()):
            if analyses:
                status = analyses[0].get('status', 'unknown')
                print(f"  {camera_name}: {status}")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
