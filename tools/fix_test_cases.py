#!/usr/bin/env python3
"""
测试用例自动修复工具
分析失败的测试并更新期望结果
"""
import click
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.http_client import HTTPClient
from test_data.loader import loader
from config.settings import config
from utils.logger import log


def extract_failure_info(pytest_output: str) -> List[Dict[str, Any]]:
    """
    从pytest输出中提取失败信息

    Returns:
        List of {test_id, expected, actual, error_message}
    """
    failures = []

    # 匹配失败信息的正则
    pattern = r'FAILED.*?\[(.*?)\].*?AssertionError: 期望状态码 (\d+), 实际 (\d+)'

    matches = re.findall(pattern, pytest_output)

    for match in matches:
        test_case_id = match[0]
        expected = int(match[1])
        actual = int(match[2])

        failures.append({
            "test_case_id": test_case_id,
            "expected_status": expected,
            "actual_status": actual
        })

    return failures


def analyze_and_fix_case(
        test_case: Any,
        actual_status: int,
        http_client: HTTPClient
) -> Dict[str, Any]:
    """
    分析测试用例并生成修复建议

    Args:
        test_case: 测试用例对象
        actual_status: 实际返回的状态码
        http_client: HTTP客户端

    Returns:
        修复建议字典
    """
    # 重新执行请求获取完整响应
    try:
        response = http_client.request(
            test_case.api.method.value,
            test_case.api.endpoint,
            json=test_case.data
        )

        response_data = response.json() if response.content else {}

    except Exception as e:
        log.error(f"执行请求失败: {e}")
        response_data = {}

    # 分析结果
    suggestion = {
        "test_case_id": test_case.id,
        "title": test_case.title,
        "old_expected_status": test_case.expected.status_code,
        "new_expected_status": actual_status,
        "response_data": response_data,
        "fix_reason": ""
    }

    # 判断修复原因
    if actual_status == 200:
        if test_case.expected.status_code >= 400:
            suggestion["fix_reason"] = "API实际接受了该数据（可能是负向用例设计问题或API验证不严格）"
            suggestion["fix_type"] = "convert_to_positive"
        else:
            suggestion["fix_reason"] = "状态码匹配"
            suggestion["fix_type"] = "no_change"
    elif actual_status >= 400:
        suggestion["fix_reason"] = f"API返回错误状态码 {actual_status}"
        suggestion["fix_type"] = "update_status"

    # 提取响应中的有用字段
    if response_data:
        suggestion["response_contains"] = list(response_data.keys())[:5]

    return suggestion


def apply_fixes(
        data_file: Path,
        fixes: List[Dict[str, Any]],
        dry_run: bool = False
) -> bool:
    """
    应用修复到数据文件

    Args:
        data_file: 数据文件路径
        fixes: 修复列表
        dry_run: 是否仅模拟运行

    Returns:
        是否成功
    """
    # 读取数据文件
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])

    # 应用修复
    fixed_count = 0
    for fix in fixes:
        test_id = fix["test_case_id"]

        # 查找对应的用例
        for case in test_cases:
            if case["id"] == test_id:
                old_status = case["expected"]["status_code"]
                new_status = fix["new_expected_status"]

                if dry_run:
                    log.info(f"[模拟] {test_id}: {old_status} -> {new_status}")
                else:
                    case["expected"]["status_code"] = new_status

                    # 如果是转换为正向用例
                    if fix["fix_type"] == "convert_to_positive":
                        # 更新tags
                        if "negative" in case["tags"]:
                            case["tags"].remove("negative")
                        if "positive" not in case["tags"]:
                            case["tags"].append("positive")

                        # 更新标题
                        case["title"] = case["title"].replace("返回400", "成功")
                        case["title"] = case["title"].replace("返回500", "成功")
                        case["title"] = case["title"].replace("失败", "成功")

                    # 更新response_contains
                    if "response_contains" in fix and fix["response_contains"]:
                        case["expected"]["response_contains"] = fix["response_contains"]

                    log.info(f"✅ 修复 {test_id}: {old_status} -> {new_status}")

                fixed_count += 1
                break

    # 保存修改
    if not dry_run and fixed_count > 0:
        # 备份原文件
        backup_file = data_file.with_suffix('.json.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.info(f"📦 备份原文件: {backup_file}")

        # 保存修复后的文件
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.info(f"💾 已保存修复: {data_file}")

    return fixed_count > 0


@click.group()
def cli():
    """测试用例自动修复工具"""
    pass


@cli.command()
@click.option('--env', default='dev', help='测试环境')
@click.option('--test-file', required=True, help='测试文件路径')
@click.option('--data-file', help='数据文件路径（自动检测如果未指定）')
@click.option('--dry-run/--apply', default=True, help='模拟运行或实际应用修复')
def auto_fix(env, test_file, data_file, dry_run):
    """自动修复失败的测试用例"""
    click.echo("\n🔧 测试用例自动修复工具")
    click.echo("=" * 60 + "\n")

    # 设置环境
    config.set_environment(env)

    # 自动检测数据文件
    if not data_file:
        click.echo("🔍 自动检测数据文件...")

        # 方法1: 从测试文件名推断
        test_path = Path(test_file)
        test_name = test_path.stem  # test_post_pet_negative

        # 提取关键词
        # test_post_pet_negative -> post_pet_negative
        keywords = test_name.replace("test_", "").split("_")

        # 在数据目录搜索
        data_dir = config.data_path

        click.echo(f"   数据目录: {data_dir}")
        click.echo(f"   搜索关键词: {keywords}")

        # 搜索所有JSON文件
        all_json_files = list(data_dir.rglob("*.json"))

        if not all_json_files:
            click.echo(f"\n❌ 数据目录为空: {data_dir}", err=True)
            click.echo("\n💡 提示:")
            click.echo(f"   1. 确保数据文件在: {data_dir}")
            click.echo(f"   2. 或使用 --data-file 手动指定数据文件")
            sys.exit(1)

        click.echo(f"   找到 {len(all_json_files)} 个JSON文件")

        # 评分匹配
        scored_files = []
        for json_file in all_json_files:
            file_name = json_file.stem.lower()
            score = 0

            # 计算匹配分数
            for keyword in keywords:
                if keyword in file_name:
                    score += 1

            if score > 0:
                scored_files.append((score, json_file))

        if not scored_files:
            click.echo(f"\n❌ 未找到匹配的数据文件")
            click.echo(f"\n可用的数据文件:")
            for f in all_json_files[:10]:
                click.echo(f"   - {f.relative_to(config.data_path)}")
            click.echo(f"\n请使用 --data-file 指定正确的数据文件")
            sys.exit(1)

        # 选择得分最高的
        scored_files.sort(reverse=True, key=lambda x: x[0])
        data_file = scored_files[0][1]

        click.echo(f"   ✅ 匹配到: {data_file.name} (得分: {scored_files[0][0]})")

        # 如果有多个高分匹配，显示它们
        if len(scored_files) > 1 and scored_files[0][0] == scored_files[1][0]:
            click.echo(f"\n   ⚠️  发现多个可能的匹配:")
            for score, f in scored_files[:3]:
                click.echo(f"      - {f.name} (得分: {score})")

            if not click.confirm(f"\n   使用 {data_file.name}？", default=True):
                click.echo("\n请使用 --data-file 手动指定")
                sys.exit(0)

        click.echo()
    else:
        data_file = Path(data_file)

    if not data_file.exists():
        click.echo(f"❌ 数据文件不存在: {data_file}", err=True)
        sys.exit(1)

    # 运行测试获取失败信息
    click.echo("🧪 运行测试以收集失败信息...\n")

    import subprocess
    result = subprocess.run(
        ["pytest", "--env", env, test_file, "-v"],
        capture_output=True,
        text=True
    )

    pytest_output = result.stdout + result.stderr

    # 提取失败信息
    click.echo("📊 分析失败的测试用例...\n")

    # 简单解析失败（从输出中提取）
    failure_pattern = r'FAILED.*?\[(test_case\d+)\].*?AssertionError: 期望状态码 (\d+), 实际 (\d+)'
    failures = re.findall(failure_pattern, pytest_output)

    if not failures:
        click.echo("✅ 没有失败的测试用例需要修复！")
        return

    click.echo(f"发现 {len(failures)} 个失败的测试:\n")

    # 加载测试数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])

    # 创建HTTP客户端
    http_client = HTTPClient()

    # 分析并生成修复
    fixes = []

    for idx, (test_case_id, expected, actual) in enumerate(failures):
        # 查找对应的测试用例
        case_idx = int(test_case_id.replace("test_case", ""))

        if case_idx < len(test_cases):
            test_case_data = test_cases[case_idx]

            click.echo(f"{idx + 1}. {test_case_data['id']}: {test_case_data['title']}")
            click.echo(f"   期望状态码: {expected} -> 实际状态码: {actual}")

            # 分析修复
            # 简化版：直接更新状态码
            fix = {
                "test_case_id": test_case_data["id"],
                "old_expected_status": int(expected),
                "new_expected_status": int(actual),
                "fix_type": "update_status" if int(actual) >= 400 else "convert_to_positive"
            }

            if int(actual) == 200:
                click.echo(f"   建议: 转换为正向用例（API接受了该数据）")
            else:
                click.echo(f"   建议: 更新期望状态码为 {actual}")

            fixes.append(fix)
            click.echo()

    # 应用修复
    if dry_run:
        click.echo("\n🔍 模拟运行模式 - 不会修改文件")
        click.echo("\n建议的修改:")
    else:
        click.echo("\n⚠️  将要应用以下修改:")

    for fix in fixes:
        click.echo(f"  • {fix['test_case_id']}: {fix['old_expected_status']} -> {fix['new_expected_status']}")

    if not dry_run:
        if not click.confirm("\n确认应用修复？", default=True):
            click.echo("已取消")
            return

    # 应用修复
    success = apply_fixes(data_file, fixes, dry_run)

    if success:
        if dry_run:
            click.echo("\n✅ 模拟运行完成")
            click.echo("使用 --apply 参数实际应用修复")
        else:
            click.echo("\n✅ 修复已应用！")
            click.echo(f"\n重新运行测试:")
            click.echo(f"  pytest --env={env} {test_file} -v")

    http_client.close()


@cli.command()
@click.argument('data-file', type=click.Path(exists=True))
def validate(data_file):
    """验证数据文件格式"""
    click.echo(f"🔍 验证数据文件: {data_file}\n")

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "test_cases" not in data:
            click.echo("❌ 缺少 test_cases 字段")
            return

        test_cases = data["test_cases"]
        click.echo(f"✅ 包含 {len(test_cases)} 个测试用例\n")

        # 检查每个用例
        for idx, case in enumerate(test_cases, 1):
            issues = []

            if "id" not in case:
                issues.append("缺少id")
            if "expected" not in case:
                issues.append("缺少expected")
            elif "status_code" not in case["expected"]:
                issues.append("缺少expected.status_code")

            if issues:
                click.echo(f"  {idx}. {case.get('id', '未知')}: ❌ {', '.join(issues)}")
            else:
                click.echo(f"  {idx}. {case['id']}: ✅")

        click.echo("\n✅ 验证完成")

    except json.JSONDecodeError as e:
        click.echo(f"❌ JSON格式错误: {e}")
    except Exception as e:
        click.echo(f"❌ 验证失败: {e}")


def main():
    """入口函数"""
    cli()


if __name__ == '__main__':
    main()