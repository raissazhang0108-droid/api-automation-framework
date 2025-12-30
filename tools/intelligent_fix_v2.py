#!/usr/bin/env python3
"""
智能测试修复工具 v2
简化版本，更可靠的失败检测
"""
import click
import json
import sys
import subprocess
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent import create_generator
from ai_agent.test_fixer_agent import TestFixerAgent
from core.http_client import HTTPClient
from config.settings import config
from utils.logger import log


def detect_data_file(test_file: str, env: str) -> Path:
    """自动检测数据文件"""
    test_path = Path(test_file)
    test_name = test_path.stem
    keywords = test_name.replace("test_", "").split("_")

    data_dir = config.data_path
    all_json_files = list(data_dir.rglob("*.json"))

    scored_files = []
    for json_file in all_json_files:
        file_name = json_file.stem.lower()
        score = sum(1 for keyword in keywords if keyword in file_name)
        if score > 0:
            scored_files.append((score, json_file))

    if not scored_files:
        raise FileNotFoundError("未找到匹配的数据文件")

    scored_files.sort(reverse=True, key=lambda x: x[0])
    return scored_files[0][1]


def run_tests_and_get_output(test_file: str, env: str) -> tuple:
    """运行测试并返回输出和返回码"""
    result = subprocess.run(
        ["pytest", "--env", env, test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    # 保存
    Path("reports").mkdir(exist_ok=True)
    Path("reports/pytest_output.txt").write_text(output, encoding='utf-8')

    return output, result.returncode


def parse_failures_from_output(output: str) -> list:
    """从pytest输出解析失败"""
    failures = []
    lines = output.split('\n')

    # 查找所有FAILED的test_case
    failed_cases = set()
    for line in lines:
        if 'FAILED' in line and 'test_case' in line:
            match = re.search(r'test_case(\d+)', line)
            if match:
                failed_cases.add(int(match.group(1)))

    # 为每个失败的用例查找详细信息
    for case_idx in sorted(failed_cases):
        # 在输出中查找这个case的AssertionError
        pattern = f"test_case{case_idx}.*?AssertionError: 期望状态码 (\\d+), 实际 (\\d+)"
        match = re.search(pattern, output, re.DOTALL)

        if match:
            expected = int(match.group(1))
            actual = int(match.group(2))
        else:
            # 默认假设
            expected = 400
            actual = 200

        failures.append({
            "test_case_index": case_idx,
            "expected_status": expected,
            "actual_status": actual,
            "error_message": f"期望状态码 {expected}, 实际 {actual}",
            "response_data": {}
        })

    return failures


@click.command()
@click.option('--test-file', required=True)
@click.option('--data-file', default=None)
@click.option('--env', default='dev')
@click.option('--provider', default='ollama')
@click.option('--model', default=None)
@click.option('--interactive/--auto', default=True)
def main(test_file, data_file, env, provider, model, interactive):
    """智能测试修复 v2"""

    click.echo("\n🤖 智能测试修复工具 v2")
    click.echo("=" * 60 + "\n")

    config.set_environment(env)

    # 检测数据文件
    if not data_file:
        click.echo("🔍 自动检测数据文件...")
        try:
            data_file = detect_data_file(test_file, env)
            click.echo(f"   ✅ {data_file.name}\n")
        except Exception as e:
            click.echo(f"   ❌ {e}")
            sys.exit(1)
    else:
        data_file = Path(data_file)

    # 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])
    click.echo(f"📊 测试数据: {len(test_cases)} 个用例\n")

    # 运行测试
    click.echo("🧪 运行测试...\n")
    output, returncode = run_tests_and_get_output(test_file, env)

    if returncode == 0:
        click.echo("✅ 所有测试通过！")
        return

    # 解析失败
    failures = parse_failures_from_output(output)

    if not failures:
        click.echo("⚠️  发现失败但无法解析详情")
        click.echo("   查看: reports/pytest_output.txt")
        return

    click.echo(f"📋 发现 {len(failures)} 个失败\n")

    # 初始化AI
    click.echo(f"🤖 初始化AI引擎 ({provider})...")
    try:
        ai_generator = create_generator(provider=provider, model=model)
        fixer_agent = TestFixerAgent(ai_generator.agent)
        click.echo("   ✅ AI就绪\n")
    except Exception as e:
        click.echo(f"   ⚠️  使用规则引擎\n")

        class DummyAgent:
            pass

        fixer_agent = TestFixerAgent(DummyAgent())

    # HTTP客户端
    http_client = HTTPClient()

    # 分析和修复
    fixed_cases = []

    for failure in failures:
        idx = failure['test_case_index']

        if idx >= len(test_cases):
            continue

        test_case = test_cases[idx]

        click.echo(f"📋 {test_case['id']}")
        click.echo(f"   {test_case['title']}")
        click.echo(f"   期望: {failure['expected_status']} -> 实际: {failure['actual_status']}")

        # 分析
        click.echo("   🧠 分析...")
        try:
            analysis = fixer_agent.analyze_failure(test_case, failure)
        except Exception as e:
            click.echo(f"   ❌ 分析失败: {e}")
            continue

        click.echo(f"   原因: {analysis.get('root_cause', '未知')}")

        strategies = analysis.get('fix_strategies', [])
        if not strategies:
            click.echo("   ⚠️  无修复策略\n")
            continue

        click.echo("\n   修复策略:")
        for i, s in enumerate(strategies):
            prefix = "   🌟" if i == analysis.get('recommended_strategy', 0) else "     "
            click.echo(f"{prefix} {i + 1}. {s['description']} ({s['confidence']:.0%})")

        # 选择策略
        if interactive:
            choice = click.prompt("\n   选择 (0=跳过)", type=int, default=1)
            if choice == 0:
                click.echo("   ⏭️  跳过\n")
                continue
            selected = strategies[choice - 1] if 0 < choice <= len(strategies) else strategies[0]
        else:
            selected = strategies[analysis.get('recommended_strategy', 0)]

        # 应用
        try:
            fixed_case = fixer_agent.apply_fix(test_case, selected)
            fixed_cases.append((idx, fixed_case))
            click.echo(f"   ✅ 应用: {selected['strategy']}\n")
        except Exception as e:
            click.echo(f"   ❌ 失败: {e}\n")

    http_client.close()

    # 保存
    if fixed_cases:
        click.echo(f"\n💾 保存 {len(fixed_cases)} 个修复...")

        # 备份
        backup = data_file.with_suffix('.json.backup')
        with open(backup, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        click.echo(f"   备份: {backup}")

        # 应用
        for idx, fixed in fixed_cases:
            test_cases[idx] = fixed

        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(f"   ✅ 完成")

        # 重新测试
        if click.confirm("\n🧪 重新测试？", default=True):
            click.echo()
            subprocess.run(["pytest", "--env", env, test_file, "-v"])

    click.echo("\n✨ 完成\n")


if __name__ == '__main__':
    main()