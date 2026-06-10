#!/usr/bin/env python3
"""
copyright-architect 验证脚本
验证软件著作权申请材料是否符合2026年审查要求

用法：
    python3 validate.py <output_dir>

返回值：
    0 = 全部通过（无 FAIL）
    1 = 有 WARN（无 FAIL）
    2 = 有 FAIL（需修正）
"""

import sys
import re
import os
from datetime import datetime
from pathlib import Path


# ─── 颜色输出 ────────────────────────────────────────────────────────────────

def green(s): return f"\033[32m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


# ─── 结果收集 ────────────────────────────────────────────────────────────────

results = {"PASS": [], "WARN": [], "FAIL": []}

def record(level, category, message, detail=""):
    entry = {"category": category, "message": message, "detail": detail}
    results[level].append(entry)
    icon = {"PASS": green("✅"), "WARN": yellow("⚠️"), "FAIL": red("❌")}[level]
    print(f"  {icon} {message}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"     {line}")


# ─── 文件读取 ────────────────────────────────────────────────────────────────

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception as e:
        return None


# ─── 字段提取工具 ────────────────────────────────────────────────────────────

def extract_table_value(text, key):
    """从 Markdown 表格中提取 | key | value | 格式的值"""
    pattern = rf"\|\s*\*{{0,2}}{re.escape(key)}\*{{0,2}}\s*\|\s*([^|\n]+?)\s*\|"
    m = re.search(pattern, text)
    if m:
        val = m.group(1).strip()
        # 排除占位符
        if re.search(r"^\[.*\]$", val):
            return None
        return val
    return None


def extract_heading_section(text, heading_pattern, next_heading_level=2):
    """提取某个标题下的内容（到下一个同级标题为止）"""
    pattern = rf"(?:^|\n)(#{{{next_heading_level}}}[^#\n]*{heading_pattern}[^\n]*)\n(.*?)(?=\n#{{{next_heading_level}}}[^#]|\Z)"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(2)
    return ""


def count_chinese_words(text):
    """统计中文字符数 + 英文单词数"""
    # 去除 Markdown 代码块
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 中文字符
    chinese = len(re.findall(r"[一-鿿㐀-䶿]", text))
    # 英文单词
    english = len(re.findall(r"\b[a-zA-Z]{2,}\b", text))
    return chinese + english


# ─── 占位符检测 ──────────────────────────────────────────────────────────────

PLACEHOLDER_PATTERNS = [
    r"\[在此填写[^\]]*\]",
    r"\[如：[^\]]*\]",
    r"\[描述[^\]]*\]",
    r"\[功能描述[^\]]*\]",
    r"\[详细描述[^\]]*\]",
    r"\[YYYY年MM月DD日\]",
    r"\[著作权人名称\]",
    r"\[软件全称[^\]]*\]",
    r"\[品牌[^\]]*\]",
    r"\[单位全称[^\]]*\]",
    r"\[字段\d+\]",
    r"\[组件名\]",
    r"\[工具名称\]",
    r"\[版本\]",
    r"\[许可证[^\]]*\]",
    r"\[步骤\d+\]",
    r"\[功能\d+名称\]",
    r"\[模块\d+名称\]",
    r"\[技术特点\d+\]",
    r"\[层\d+名称\]",
    r"\[表\d+名称\]",
    r"\[表名：[^\]]*\]",
    r"\[核心算法/逻辑\d+名称\]",
    r"\[问题\d+\]",
    r"\[常见问题\d+\]",
    r"\[截图占位[^\]]*\]",
]


def find_placeholders(text):
    """返回所有未替换占位符的列表"""
    found = []
    for pat in PLACEHOLDER_PATTERNS:
        for m in re.finditer(pat, text):
            found.append(m.group(0))
    return list(set(found))


# ─── 验证模块 ────────────────────────────────────────────────────────────────

def validate_consistency(form_text, manual_text):
    """Step 4.1: 一致性验证"""
    print(bold("\n[一致性验证]"))

    # 从申请表提取关键字段
    form_name = extract_table_value(form_text, "软件全称")
    form_version = extract_table_value(form_text, "版本号")
    form_owner = extract_table_value(form_text, "著作权人名称")
    form_date = extract_table_value(form_text, "开发完成日期")

    # 从说明书封面提取（查找封面区域）
    # 封面通常在文档开头，查找 "软件全称"、"版本号"、"著作权人" 行
    manual_name_m = re.search(r"^#\s+(.+?)\s*$", manual_text, re.MULTILINE)
    manual_name = manual_name_m.group(1).strip() if manual_name_m else None
    # 去掉标题中的版本号部分（如 "XX软件 V1.0" → "XX软件"）
    if manual_name:
        manual_name = re.sub(r"\s+V\d+\.\d+.*$", "", manual_name).strip()

    manual_version_m = re.search(r"\*\*版本号\*\*[：:]\s*([^\n\|]+)", manual_text)
    if not manual_version_m:
        manual_version_m = re.search(r"\|\s*版本号\s*\|\s*([^\|\n]+)", manual_text)
    manual_version = manual_version_m.group(1).strip() if manual_version_m else None

    manual_owner_m = re.search(r"\*\*著作权人\*\*[：:]\s*([^\n\|]+)", manual_text)
    if not manual_owner_m:
        manual_owner_m = re.search(r"\|\s*著作权人\s*\|\s*([^\|\n]+)", manual_text)
    manual_owner = manual_owner_m.group(1).strip() if manual_owner_m else None

    # 比对
    fields = [
        ("软件全称", form_name, manual_name),
        ("版本号", form_version, manual_version),
        ("著作权人", form_owner, manual_owner),
    ]

    for field, form_val, manual_val in fields:
        if not form_val:
            record("WARN", "一致性", f"{field}：申请表中未找到该字段")
            continue
        if not manual_val:
            record("WARN", "一致性", f"{field}：说明书中未找到该字段")
            continue
        if form_val.strip() == manual_val.strip():
            record("PASS", "一致性", f"{field}一致：{form_val}")
        else:
            record("FAIL", "一致性",
                   f"{field}不一致",
                   f"申请表：\"{form_val}\"\n说明书：\"{manual_val}\"")

    # 开发完成日期（说明书1.1表格）
    manual_date_m = re.search(r"\|\s*开发完成日期\s*\|\s*([^\|\n]+)", manual_text)
    manual_date = manual_date_m.group(1).strip() if manual_date_m else None
    if form_date and manual_date:
        if form_date.strip() == manual_date.strip():
            record("PASS", "一致性", f"开发完成日期一致：{form_date}")
        else:
            record("FAIL", "一致性",
                   "开发完成日期不一致",
                   f"申请表：\"{form_date}\"\n说明书：\"{manual_date}\"")


def validate_structure(manual_text):
    """Step 4.2: 结构完整性验证"""
    print(bold("\n[结构完整性验证]"))

    required_sections = [
        ("软件概述|第1章", "第1章 软件概述", "FAIL"),
        ("功能模块|第2章", "第2章 功能模块与流程图", "FAIL"),
        ("操作步骤|使用说明|第3章", "第3章 操作步骤与使用说明", "FAIL"),
        ("设计说明|第4章", "第4章 设计说明", "FAIL"),
        ("测试|第5章", "第5章 测试与维护", "FAIL"),
        ("附录|声明", "附录 声明", "FAIL"),
        ("PDF格式化规范|格式化规范", "附录B PDF格式化规范", "FAIL"),
        ("AI辅助|人工智能|未使用AI|未使用任何AI", "AI辅助开发声明", "FAIL"),
    ]

    recommended_sections = [
        ("数据库|ER图|表结构", "数据库设计", "WARN"),
        ("安全|加密|认证", "安全机制", "WARN"),
        ("测试用例|测试结果", "测试用例与结果", "WARN"),
        ("mermaid|```mermaid|graph TD|graph LR|flowchart", "Mermaid图表", "WARN"),
    ]

    for pattern, label, level in required_sections:
        if re.search(pattern, manual_text, re.IGNORECASE):
            record("PASS", "结构", f"{label}：存在")
        else:
            record(level, "结构", f"{label}：缺失")

    for pattern, label, level in recommended_sections:
        if re.search(pattern, manual_text, re.IGNORECASE):
            record("PASS", "结构", f"{label}：存在")
        else:
            record(level, "结构", f"{label}：缺失（建议补充）")

    # 占位符检测
    placeholders = find_placeholders(manual_text)
    if placeholders:
        detail = "\n".join(f"- {p}" for p in placeholders[:10])
        if len(placeholders) > 10:
            detail += f"\n... 共 {len(placeholders)} 处"
        record("FAIL", "结构", f"发现 {len(placeholders)} 处未替换占位符", detail)
    else:
        record("PASS", "结构", "无未替换占位符")


def validate_word_count(manual_text, form_text):
    """Step 4.3: 字数与内容密度验证"""
    print(bold("\n[字数验证]"))

    total = count_chinese_words(manual_text)
    if total >= 3000:
        record("PASS", "字数", f"总字数：{total:,}字（要求≥3000字）")
    else:
        record("FAIL", "字数", f"总字数不足：{total:,}字（要求≥3000字，缺少约{3000-total}字）")

    # 各章节字数
    chapter_thresholds = [
        ("第3章", "操作步骤与使用说明", 500, "WARN"),
        ("第4章", "设计说明", 600, "WARN"),
    ]

    for ch_num, ch_name, threshold, level in chapter_thresholds:
        # 提取章节内容（从该章标题到下一章标题）
        pattern = rf"(?:^|\n)(#{1,2}\s*{ch_num}[^\n]*)\n(.*?)(?=\n#{1,2}\s*第\d+章|\n#{1,2}\s*附录|\Z)"
        m = re.search(pattern, manual_text, re.DOTALL | re.IGNORECASE)
        if m:
            section_text = m.group(2)
            section_words = count_chinese_words(section_text)
            if section_words >= threshold:
                record("PASS", "字数", f"{ch_name}：{section_words:,}字（建议≥{threshold}字）")
            else:
                record(level, "字数", f"{ch_name}字数偏少：{section_words:,}字（建议≥{threshold}字）")

    # 申请表主要功能字数
    func_m = re.search(r"###\s*主要功能[^\n]*\n+(.*?)(?=\n###|\n##|\Z)", form_text, re.DOTALL)
    if func_m:
        func_text = func_m.group(1).strip()
        func_words = count_chinese_words(func_text)
        if func_words >= 100:
            record("PASS", "字数", f"申请表主要功能描述：{func_words:,}字（要求≥100字）")
        else:
            record("FAIL", "字数", f"申请表主要功能描述不足：{func_words:,}字（要求≥100字）")


def validate_format(form_text, manual_text):
    """Step 4.4: 格式与审查红线验证"""
    print(bold("\n[格式与审查红线验证]"))

    # 版本号格式
    version_m = re.search(r"\|\s*\*{0,2}版本号\*{0,2}\s*\|\s*([^\|\n]+)", form_text)
    if version_m:
        version = version_m.group(1).strip()
        if re.match(r"^V\d+\.\d+", version):
            record("PASS", "格式", f"版本号格式正确：{version}")
        else:
            record("FAIL", "格式", f"版本号格式错误：\"{version}\"（应为 V1.0 格式）")
    else:
        record("WARN", "格式", "未找到版本号字段")

    # 软件全称以"软件"结尾
    name_m = re.search(r"\|\s*\*{0,2}软件全称\*{0,2}\s*\|\s*([^\|\n]+)", form_text)
    if name_m:
        name = name_m.group(1).strip()
        if name.endswith("软件"):
            record("PASS", "格式", f'软件全称以"软件"结尾：{name}')
        elif re.search(r"^\[.*\]$", name):
            record("FAIL", "格式", "软件全称未填写（仍为占位符）")
        else:
            record("FAIL", "格式", f'软件全称未以"软件"结尾："{name}"')
    else:
        record("WARN", "格式", "未找到软件全称字段")

    # 源程序量
    loc_m = re.search(r"\|\s*\*{0,2}源程序量\*{0,2}\s*\|\s*([^\|\n]+)", form_text)
    if loc_m:
        loc = loc_m.group(1).strip()
        if re.search(r"^\[.*\]$", loc) or loc in ("", "0"):
            record("FAIL", "格式", "源程序量未填写")
        elif re.search(r"\d", loc):
            record("PASS", "格式", f"源程序量已填写：{loc}")
        else:
            record("WARN", "格式", f"源程序量格式可能有误：\"{loc}\"")
    else:
        record("WARN", "格式", "未找到源程序量字段")

    # AI辅助声明字段存在性
    if re.search(r"AI辅助开发声明|AI工具|人工智能辅助", form_text, re.IGNORECASE):
        record("PASS", "格式", "申请表中存在AI辅助开发声明字段")
    else:
        record("FAIL", "格式", "申请表中缺少AI辅助开发声明字段（2026年新规要求）")

    # 说明书附录A声明完整性
    appendix_m = re.search(r"附录A[：:]?\s*声明(.*?)(?=附录B|\Z)", manual_text, re.DOTALL | re.IGNORECASE)
    if appendix_m:
        appendix_text = appendix_m.group(1)
        # AI声明完整性
        has_tool_name = bool(re.search(r"GitHub Copilot|ChatGPT|Claude|Cursor|Codeium|Tabnine|通义灵码|文心一言|未使用|完全由人工", appendix_text, re.IGNORECASE))
        has_ratio = bool(re.search(r"\d+%|人工创作比例|100%", appendix_text))
        if has_tool_name:
            record("PASS", "声明", "AI辅助声明包含工具名称")
        else:
            record("WARN", "声明", "AI辅助声明中未明确工具名称（或未声明未使用AI）")
        if has_ratio:
            record("PASS", "声明", "AI辅助声明包含人工创作比例")
        else:
            record("WARN", "声明", "AI辅助声明缺少人工创作比例")

        # 开源组件声明
        if re.search(r"MIT|Apache|GPL|BSD|LGPL|开源组件|未使用任何开源", appendix_text, re.IGNORECASE):
            record("PASS", "声明", "开源组件声明包含许可证信息")
        else:
            record("WARN", "声明", "开源组件声明缺少许可证类型（或未声明未使用开源组件）")
    else:
        record("WARN", "声明", "说明书中未找到附录A声明章节")


# ─── 报告生成 ────────────────────────────────────────────────────────────────

def generate_report(output_dir, software_name, version):
    """生成 03-验证报告.md"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fail_count = len(results["FAIL"])
    warn_count = len(results["WARN"])
    pass_count = len(results["PASS"])

    if fail_count > 0:
        conclusion = "❌ 需修正（有FAIL项，不建议提交）"
    elif warn_count > 0:
        conclusion = "⚠️ 有警告（建议处理后提交）"
    else:
        conclusion = "✅ 通过（可以提交）"

    lines = [
        "# 软件著作权申请材料验证报告",
        "",
        f"**生成时间**：{now}",
        f"**软件全称**：{software_name or '（未识别）'}",
        f"**版本号**：{version or '（未识别）'}",
        f"**验证结论**：{conclusion}",
        "",
        "---",
        "",
        "## 验证结果汇总",
        "",
        f"| 类别 | PASS | WARN | FAIL |",
        f"|------|------|------|------|",
    ]

    categories = {}
    for level, items in results.items():
        for item in items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = {"PASS": 0, "WARN": 0, "FAIL": 0}
            categories[cat][level] += 1

    for cat, counts in categories.items():
        lines.append(f"| {cat} | {counts['PASS']} | {counts['WARN']} | {counts['FAIL']} |")

    lines += ["", f"**总计**：✅ {pass_count} 项通过，⚠️ {warn_count} 项警告，❌ {fail_count} 项需修正", ""]

    if results["FAIL"]:
        lines += ["---", "", "## ❌ FAIL 项（必须修正后才能提交）", ""]
        for i, item in enumerate(results["FAIL"], 1):
            lines.append(f"**{i}. [{item['category']}] {item['message']}**")
            if item["detail"]:
                for line in item["detail"].strip().split("\n"):
                    lines.append(f"   {line}")
            lines.append("")

    if results["WARN"]:
        lines += ["---", "", "## ⚠️ WARN 项（建议处理）", ""]
        for i, item in enumerate(results["WARN"], 1):
            lines.append(f"**{i}. [{item['category']}] {item['message']}**")
            if item["detail"]:
                for line in item["detail"].strip().split("\n"):
                    lines.append(f"   {line}")
            lines.append("")

    if results["PASS"]:
        lines += ["---", "", "## ✅ 通过项", ""]
        for item in results["PASS"]:
            lines.append(f"- [{item['category']}] {item['message']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 下一步操作",
        "",
    ]

    if fail_count > 0:
        lines += [
            "1. 根据上方 FAIL 项说明，修正 `01-申请表信息.md` 和 `02-软件操作说明书.md`",
            "2. 修正完成后，重新运行验证脚本：`python3 validate.py <output_dir>`",
            "3. 确认无 FAIL 项后，再提交申请",
        ]
    elif warn_count > 0:
        lines += [
            "1. 建议处理上方 WARN 项以提高申请通过率",
            "2. 处理完成后可重新运行验证脚本确认",
            "3. 提交前请确认所有文档内容真实、准确、完整",
        ]
    else:
        lines += [
            "1. 所有验证项通过，材料质量良好",
            "2. 提交前请最终人工核对文档内容的真实性",
            "3. 按照附录B的PDF格式化规范将说明书转为PDF后提交",
        ]

    report_path = Path(output_dir) / "03-验证报告.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n验证报告已保存：{report_path}")


# ─── 主函数 ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法：python3 validate.py <output_dir>")
        print("示例：python3 validate.py ./copyright-materials/")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    form_path = output_dir / "01-申请表信息.md"
    manual_path = output_dir / "02-软件操作说明书.md"

    print(bold("=== 软件著作权申请材料验证 ==="))
    print(f"验证目录：{output_dir}")
    print(f"验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查文件存在性
    form_text = read_file(form_path)
    manual_text = read_file(manual_path)

    if form_text is None:
        print(red(f"\n❌ 错误：找不到申请表文件：{form_path}"))
        sys.exit(2)
    if manual_text is None:
        print(red(f"\n❌ 错误：找不到说明书文件：{manual_path}"))
        sys.exit(2)

    # 提取软件名称和版本号（用于报告）
    name_m = re.search(r"\|\s*\*{0,2}软件全称\*{0,2}\s*\|\s*([^\|\n\[]+)", form_text)
    software_name = name_m.group(1).strip() if name_m else None
    ver_m = re.search(r"\|\s*\*{0,2}版本号\*{0,2}\s*\|\s*([^\|\n\[]+)", form_text)
    version = ver_m.group(1).strip() if ver_m else None

    if software_name:
        print(f"软件全称：{software_name}")
    if version:
        print(f"版本号：{version}")

    # 执行验证
    validate_consistency(form_text, manual_text)
    validate_structure(manual_text)
    validate_word_count(manual_text, form_text)
    validate_format(form_text, manual_text)

    # 汇总
    fail_count = len(results["FAIL"])
    warn_count = len(results["WARN"])
    pass_count = len(results["PASS"])

    print(bold("\n=== 验证结论 ==="))
    print(f"✅ 通过：{pass_count} 项")
    print(f"⚠️ 警告：{warn_count} 项")
    print(f"❌ 需修正：{fail_count} 项")

    if fail_count > 0:
        print(red(f"\n❌ 需修正（FAIL：{fail_count}项）"))
        print("FAIL 项（必须修正后才能提交）：")
        for i, item in enumerate(results["FAIL"], 1):
            print(f"  {i}. [{item['category']}] {item['message']}")
            if item["detail"]:
                for line in item["detail"].strip().split("\n"):
                    print(f"     {line}")
    elif warn_count > 0:
        print(yellow(f"\n⚠️ 有警告（WARN：{warn_count}项），建议处理后提交"))
    else:
        print(green("\n✅ 全部通过，材料质量良好"))

    # 生成报告
    generate_report(output_dir, software_name, version)

    # 返回码
    if fail_count > 0:
        sys.exit(2)
    elif warn_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
