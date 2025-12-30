#!/usr/bin/env python3
"""
智能测试修复工具
使用AI分析并修复失败的测试
"""
import click
import json
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any

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

    # 提取关键词
    keywords = test_name.replace("test_", "").split("_")

    # 搜索数据目录
    data_dir = config.data_path

    if not data_dir.exists():
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    all_json_files = list(data_dir.rglob("*.json"))

    if not all_json_files:
        raise FileNotFoundError(f"数据目录为空: {data_dir}")

    # 评分匹配
    scored_files = []
    for json_file in all_json_files:
        file_name = json_file.stem.lower()
        score = sum(1 for keyword in keywords if keyword in file_name)

        if score > 0:
            scored_files.append((score, json_file))

    if not scored_files:
        raise FileNotFoundError("未找到匹配的数据文件")

    # 返回得分最高的
    scored_files.sort(reverse=True, key=lambda x: x[0])
    return scored_files[0][1]


def run_tests_and_collect_failures(
        test_file: str,
        env: str
) -> List[Dict[str, Any]]:
    """运行测试并收集失败信息"""

    # 运行测试，使用更详细的输出
    result = subprocess.run(
        ["pytest", "--env", env, test_file, "-v", "--tb=line", "-p", "no:warnings"],
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    # 保存输出用于调试
    debug_file = Path("reports") / "pytest_output.txt"
    debug_file.parent.mkdir(exist_ok=True)
    debug_file.write_text(output, encoding='utf-8')

    # 如果测试全部通过，直接返回
    if result.returncode == 0:
        return []

    # 解析失败
    failures = []

    # 方法1: 从FAILED行提取test_case索引
    failed_pattern = r'FAILED.*?\[test_case(\d+)\]'
    failed_matches = re.findall(failed_pattern, output)

    if not failed_matches:
        # 如果没找到，返回空（但记录日志）
        log.warning("发现失败但无法解析test_case索引")
        return []

    # 方法2: 从错误输出中提取状态码
    # 分割输出，逐个分析失败用例
    lines = output.split('\n')

    # 查找所有AssertionError行
    assertion_errors = {}
    for i, line in enumerate(lines):
        if 'AssertionError: 期望状态码' in line:
            # 提取状态码
            match = re.search(r'期望状态码 (\d+), 实际 (\d+)', line)
            if match:
                expected = int(match.group(1))
                actual = int(match.group(2))

                # 向上查找对应的test_case
                for j in range(i - 1, max(0, i - 20), -1):
                    case_match = re.search(r'test_case(\d+)', lines[j])
                    if case_match:
                        case_idx = int(case_match.group(1))
                        assertion_errors[case_idx] = (expected, actual)
                        break

    # 方法3: 从响应内容中提取
    response_pattern = r'响应内容: ({[^}]*})'
    responses = re.findall(response_pattern, output)

    # 构建失败信息
    for case_idx_str in failed_matches:
        case_idx = int(case_idx_str)

        # 获取状态码信息
        if case_idx in assertion_errors:
            expected, actual = assertion_errors[case_idx]
        else:
            # 如果没有找到，尝试从其他方式获取
            # 默认假设是400->200
            expected = 400
            actual = 200

        failure = {
            "test_case_index": case_idx,
            "expected_status": expected,
            "actual_status": actual,
            "error_message": f"期望状态码 {expected}, 实际 {actual}"
        }

        # 添加响应数据
        if case_idx < len(responses):
            try:
                failure["response_data"] = json.loads(responses[case_idx])
            except:
                failure["response_data"] = {}
        else:
            failure["response_data"] = {}

        failures.append(failure)

    return failures


@click.command()
@click.option('--test-file', required=True, help='测试文件路径')
@click.option('--data-file', help='数据文件路径（自动检测）')
@click.option('--env', default='dev', help='测试环境')
@click.option('--provider',
              type=click.Choice(['openai', 'ollama', 'deepseek']),
              default='ollama',
              help='AI提供商')
@click.option('--model', help='AI模型名称')
@click.option('--interactive/--auto', default=True, help='交互式或自动修复')
def intelligent_fix(test_file, data_file, env, provider, model, interactive):
    """
    智能测试修复

    示例：
        # 交互式（推荐）
        python tools/intelligent_fix.py --test-file test_cases/test_post_pet_negative.py

        # 自动修复
        python tools/intelligent_fix.py --test-file test_cases/test_post_pet_negative.py --auto

        # 使用OpenAI
        python tools/intelligent_fix.py --test-file test_cases/test_post_pet_negative.py --provider openai
    """
    click.echo("\n🤖 智能测试修复工具 (AI驱动)")
    click.echo("=" * 60 + "\n")

    # 设置环境
    config.set_environment(env)

    # 检测数据文件
    if not data_file:
        click.echo("🔍 自动检测数据文件...")
        try:
            data_file = detect_data_file(test_file, env)
            click.echo(f"   ✅ 找到: {data_file.name}\n")
        except Exception as e:
            click.echo(f"   ❌ {e}", err=True)
            sys.exit(1)
    else:
        data_file = Path(data_file)

    if not data_file.exists():
        click.echo(f"❌ 数据文件不存在: {data_file}", err=True)
        sys.exit(1)

    # 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])

    if not test_cases:
        click.echo("❌ 数据文件中没有测试用例")
        sys.exit(1)

    # 运行测试
    click.echo("🧪 运行测试并收集失败信息...\n")
    failures = run_tests_and_collect_failures(test_file, env)

    if not failures:
        click.echo("✅ 所有测试通过！无需修复。")
        return

    click.echo(f"📊 发现 {len(failures)} 个失败的测试\n")

    # 创建AI agent
    click.echo(f"🤖 初始化AI分析引擎 ({provider})...")
    try:
        ai_generator = create_generator(provider=provider, model=model)
        fixer_agent = TestFixerAgent(ai_generator.agent)
        click.echo("   ✅ AI引擎就绪\n")
    except Exception as e:
        click.echo(f"   ⚠️  AI初始化失败: {e}")
        click.echo("   将使用规则引擎\n")

        # 创建一个简单的代理用于规则引擎
        class DummyAgent:
            pass

        fixer_agent = TestFixerAgent(DummyAgent())

    # 创建HTTP客户端
    http_client = HTTPClient()

    # 分析每个失败
    analyses = []
    fixed_cases = []

    for failure in failures:
        case_idx = failure['test_case_index']

        if case_idx >= len(test_cases):
            click.echo(f"⚠️  跳过无效索引: {case_idx}")
            continue

        test_case = test_cases[case_idx]

        click.echo(f"📋 分析: {test_case['id']}")
        click.echo(f"   标题: {test_case['title']}")
        click.echo(f"   期望: {failure['expected_status']} -> 实际: {failure['actual_status']}")

        # 重新执行获取完整响应
        try:
            response = http_client.request(
                test_case['api']['method'],
                test_case['api']['endpoint'],
                json=test_case.get('data', {})
            )
            failure['response_data'] = response.json() if response.content else {}
        except Exception as e:
            click.echo(f"   ⚠️  无法重新执行: {e}")

        # AI分析
        click.echo("   🧠 AI分析中...")
        try:
            analysis = fixer_agent.analyze_failure(test_case, failure)
        except Exception as e:
            click.echo(f"   ⚠️  分析失败: {e}")
            continue

        analyses.append(analysis)

        # 显示分析结果
        click.echo(f"   ├─ 失败类型: {analysis.get('failure_type', 'unknown')}")
        click.echo(f"   └─ 根本原因: {analysis.get('root_cause', '未知')}")

        # 显示修复策略
        strategies = analysis.get('fix_strategies', [])
        recommended_idx = analysis.get('recommended_strategy', 0)

        if not strategies:
            click.echo("   ⚠️  没有可用的修复策略\n")
            continue

        click.echo("\n   修复策略:")
        for i, strategy in enumerate(strategies):
            prefix = "   🌟" if i == recommended_idx else "     "
            click.echo(f"{prefix} {i + 1}. {strategy['description']}")
            click.echo(f"        置信度: {strategy['confidence']:.0%}")

        # 交互式选择或自动应用
        if interactive:
            click.echo()
            choice = click.prompt(
                "   选择策略 (1-{}, 0=跳过)".format(len(strategies)),
                type=int,
                default=recommended_idx + 1
            )

            if choice == 0:
                click.echo("   ⏭️  跳过此用例\n")
                continue

            if choice < 1 or choice > len(strategies):
                click.echo("   ❌ 无效选择，跳过\n")
                continue

            selected_strategy = strategies[choice - 1]
        else:
            selected_strategy = strategies[recommended_idx]

        # 应用修复
        try:
            fixed_case = fixer_agent.apply_fix(test_case, selected_strategy)
            fixed_cases.append((case_idx, fixed_case))
            click.echo(f"   ✅ 将应用: {selected_strategy['strategy']}\n")
        except Exception as e:
            click.echo(f"   ❌ 修复失败: {e}\n")

    http_client.close()

    # 保存修复
    if fixed_cases:
        click.echo(f"\n💾 保存修复...")

        # 备份
        backup_file = data_file.with_suffix('.json.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        click.echo(f"   📦 备份: {backup_file}")

        # 应用修复
        for idx, fixed_case in fixed_cases:
            test_cases[idx] = fixed_case

        # 保存
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        click.echo(f"   ✅ 已修复 {len(fixed_cases)} 个用例")

        # 生成报告
        if analyses:
            report = fixer_agent.generate_fix_report(analyses)
            report_file = Path("reports") / "fix_analysis.md"
            report_file.parent.mkdir(exist_ok=True, parents=True)
            report_file.write_text(report, encoding='utf-8')

            click.echo(f"\n📄 分析报告: {report_file}")

        # 重新运行测试
        if click.confirm("\n🧪 重新运行测试？", default=True):
            click.echo("\n" + "=" * 60)
            click.echo("重新运行测试")
            click.echo("=" * 60 + "\n")

            result = subprocess.run(
                ["pytest", "--env", env, test_file, "-v"],
                text=True
            )

            if result.returncode == 0:
                click.echo("\n✅ 所有测试通过！")
            else:
                click.echo("\n⚠️  仍有测试失败，可能需要进一步调整")
    else:
        click.echo("\n⚠️  没有应用任何修复")

    click.echo("\n✨ 完成！\n")


if __name__ == '__main__':
    intelligent_fix()