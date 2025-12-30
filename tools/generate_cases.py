#!/usr/bin/env python3
"""
AI测试用例生成工具
支持OpenAI、Ollama、DeepSeek
"""
import click
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent import create_generator, AIProvider
from utils.logger import log


def create_test_file(output_dir: Path, spec_file: str, test_type: str) -> Path:
    """
    生成对应的测试文件
    """
    # 从spec文件名提取API名称
    spec_path = Path(spec_file)
    api_name = spec_path.stem.replace('__', '_').lower()

    # 确定测试文件输出目录
    test_cases_dir = Path("test_cases")
    test_cases_dir.mkdir(exist_ok=True)

    # 生成测试文件名
    test_file = test_cases_dir / f"test_{api_name}_{test_type}.py"

    # 从output_dir推断数据文件的相对路径
    data_parts = output_dir.parts
    if 'test_data' in data_parts:
        idx = data_parts.index('test_data')
        category = '/'.join(data_parts[idx + 2:]) if len(data_parts) > idx + 2 else None
    else:
        category = None

    # 生成测试代码
    test_code = f'''"""
{api_name.upper()} API 测试
自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_data.selector import select
from test_data.loader import loader
from utils.assertions import APIAssertions


class Test{api_name.replace('_', '').title()}:
    """
    {api_name.upper()} 测试套件
    """

    @pytest.mark.parametrize(
        "test_case",
        select()
            {''.join([f'.from_category("{category}")' if category else ''])}
            .with_tags(["{test_type}"])
            .for_environment()
            .get()
    )
    def test_{test_type}_cases(self, api_client, test_case):
        """{test_type.title()} 测试用例"""
        # 发送请求
        response = api_client.request(
            test_case.api.method.value,
            test_case.api.endpoint,
            json=test_case.data,
            test_name=test_case.id
        )

        # 断言状态码
        APIAssertions.assert_status_code(
            response,
            test_case.expected.status_code
        )

        # 断言响应包含字段
        if hasattr(test_case.expected, 'response_contains') and test_case.expected.response_contains:
            try:
                APIAssertions.assert_response_contains(
                    response,
                    test_case.expected.response_contains
                )
            except AssertionError as e:
                log.warning(f"响应字段断言失败: {{e}}")

        # 负向测试的额外断言
        if "{test_type}" == "negative" and hasattr(test_case.expected, 'error_code'):
            if test_case.expected.error_code:
                try:
                    APIAssertions.assert_error_response(
                        response,
                        error_code=test_case.expected.error_code
                    )
                except:
                    pass


if __name__ == "__main__":
    """直接运行此文件"""
    pytest.main([__file__, "-v", "--env=dev"])
'''

    # 写入文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)

    return test_file



def create_test_file(output_dir: Path, spec_file: str, test_type: str) -> Path:
    """
    生成对应的测试文件

    Args:
        output_dir: 测试数据输出目录
        spec_file: API规格文件路径
        test_type: 测试类型

    Returns:
        生成的测试文件路径
    """
    # 从spec文件名提取API名称
    spec_path = Path(spec_file)
    api_name = spec_path.stem.replace('__', '_').lower()

    # 确定测试文件输出目录
    test_cases_dir = Path("test_cases")
    test_cases_dir.mkdir(exist_ok=True)

    # 生成测试文件名
    test_file = test_cases_dir / f"test_{api_name}_{test_type}.py"

    # 从output_dir推断数据文件的相对路径
    # 例如: test_data/dev/petstore -> petstore
    data_parts = output_dir.parts
    if 'test_data' in data_parts:
        idx = data_parts.index('test_data')
        category = '/'.join(data_parts[idx + 2:]) if len(data_parts) > idx + 2 else None
    else:
        category = None

    # 生成测试代码
    test_code = f'''"""
{api_name.upper()} API 测试
自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_data.selector import select
from test_data.loader import loader
from utils.assertions import APIAssertions


class Test{api_name.replace('_', '').title()}:
    """
    {api_name.upper()} 测试套件
    """

    @pytest.mark.parametrize(
        "test_case",
        select()
            {''.join([f'.from_category("{category}")' if category else ''])}
            .with_tags(["{test_type}"])
            .for_environment()
            .get()
    )
    def test_{test_type}_cases(self, api_client, test_case):
        """{test_type.title()} 测试用例"""
        # 发送请求
        response = api_client.request(
            test_case.api.method.value,
            test_case.api.endpoint,
            json=test_case.data,
            test_name=test_case.id
        )

        # 断言状态码
        APIAssertions.assert_status_code(
            response,
            test_case.expected.status_code
        )

        # 断言响应包含字段
        if hasattr(test_case.expected, 'response_contains') and test_case.expected.response_contains:
            try:
                APIAssertions.assert_response_contains(
                    response,
                    test_case.expected.response_contains
                )
            except AssertionError as e:
                # 某些API可能返回不同的字段结构
                log.warning(f"响应字段断言失败: {{e}}")

        # 负向测试的额外断言
        if "{test_type}" == "negative" and hasattr(test_case.expected, 'error_code'):
            if test_case.expected.error_code:
                try:
                    APIAssertions.assert_error_response(
                        response,
                        error_code=test_case.expected.error_code
                    )
                except:
                    pass


if __name__ == "__main__":
    """直接运行此文件"""
    pytest.main([__file__, "-v", "--env=dev"])
'''

    # 写入文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)

    return test_file


@click.group()
def cli():
    """AI测试用例生成工具"""
    pass


@cli.command()
@click.option('--provider',
              type=click.Choice(['openai', 'ollama', 'deepseek']),
              default='openai',
              help='AI提供商')
@click.option('--model', help='模型名称（可选）')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='API密钥')
@click.option('--spec-file',
              type=click.Path(exists=True),
              required=True,
              help='API规格文件(JSON)')
@click.option('--type',
              type=click.Choice(['positive', 'negative', 'boundary', 'security', 'all']),
              default='all',
              help='测试用例类型')
@click.option('--count', default=10, help='每种类型的生成数量')
@click.option('--output', help='输出文件名')
@click.option('--output-dir',
              type=click.Path(),
              default='test_data/ai_generated',
              help='输出目录')
@click.option('--create-test/--no-generate-test-file',
              default=True,
              help='是否同时生成测试文件')
def generate(provider, model, api_key, spec_file, type, count, output, output_dir, create_test):
    """
    生成测试用例

    示例：
        # 生成positive用例并自动创建测试文件
        python tools/generate_cases.py generate --provider ollama --spec-file specs/petstore/POST__pet.json --type positive --count 10

        # 只生成数据，不创建测试文件
        python tools/generate_cases.py generate --provider ollama --spec-file specs/petstore/POST__pet.json --type positive --no-generate-test-file
    """
    click.echo(f"\n{'=' * 60}")
    click.echo(f"AI测试用例生成工具")
    click.echo(f"{'=' * 60}\n")

    # 加载API规格
    click.echo(f"📄 加载API规格: {spec_file}")
    with open(spec_file) as f:
        api_spec = json.load(f)

    # 创建生成器
    click.echo(f"🤖 初始化AI生成器: {provider}")
    try:
        generator = create_generator(
            provider=provider,
            model=model,
            api_key=api_key
        )
    except Exception as e:
        click.echo(f"\n❌ 初始化失败: {e}", err=True)
        if provider == 'ollama':
            click.echo("\n💡 提示: 请确保Ollama服务已启动")
            click.echo("   启动命令: ollama serve")
            click.echo("   拉取模型: ollama pull llama3.2")
        sys.exit(1)

    # 生成用例
    try:
        if type == 'all':
            # 生成完整测试套件
            click.echo("\n📝 生成完整测试套件...")

            # 询问分布
            if click.confirm("是否自定义各类型用例数量？", default=False):
                positive = click.prompt("正向用例数量", type=int, default=5)
                negative = click.prompt("负向用例数量", type=int, default=10)
                boundary = click.prompt("边界用例数量", type=int, default=8)
                security = click.prompt("安全用例数量", type=int, default=5)

                distribution = {
                    "positive": positive,
                    "negative": negative,
                    "boundary": boundary,
                    "security": security
                }
            else:
                distribution = None

            with click.progressbar(
                    length=1,
                    label='生成中...',
                    show_pos=True
            ) as bar:
                result = generator.generate_suite(api_spec, distribution)
                bar.update(1)
        else:
            # 生成单一类型
            click.echo(f"\n📝 生成 {type} 用例（数量: {count}）...")

            with click.progressbar(
                    length=1,
                    label='生成中...',
                    show_pos=True
            ) as bar:
                result = generator.generate(api_spec, type, count)
                bar.update(1)

        # 显示结果
        total = len(result.get('test_cases', []))
        click.echo(f"\n✅ 成功生成 {total} 个测试用例")

        # 显示用例列表
        if click.confirm("\n是否显示用例列表？", default=True):
            click.echo("\n用例列表:")
            for idx, case in enumerate(result['test_cases'], 1):
                click.echo(f"  {idx}. {case['id']} - {case['title']}")

        # 保存数据文件
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            spec_name = Path(spec_file).stem
            output = f"{spec_name}_{type}_{timestamp}.json"

        output_path = Path(output_dir) / output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        click.echo(f"\n💾 数据文件已保存: {output_path}")

        # 生成测试文件
        if create_test:
            click.echo(f"\n🧪 生成测试文件...")
            try:
                # test_file = create_test_file(output_path.parent, spec_file, type)
                test_file = create_test_file(output_path.parent, spec_file, type)
                click.echo(f"✅ 测试文件已生成: {test_file}")

                # 显示运行命令
                click.echo(f"\n📌 运行测试:")
                click.echo(f"   pytest --env=dev {test_file} -v")
                click.echo(f"   pytest --env=dev {test_file} -v --html=reports/html/report.html --self-contained-html")

            except Exception as e:
                click.echo(f"⚠️  测试文件生成失败: {e}", err=True)
                log.exception("生成测试文件时发生错误")

        # 验证结果
        if result.get('metadata'):
            click.echo(f"\n📊 生成信息:")
            metadata = result['metadata']
            if 'distribution' in metadata:
                click.echo(f"   分布: {metadata['distribution']}")
            click.echo(f"   生成器: {metadata.get('generator', 'Unknown')}")
            click.echo(f"   模型: {metadata.get('model', 'Unknown')}")

        click.echo(f"\n{'=' * 60}")
        click.echo("✨ 完成！")
        click.echo(f"{'=' * 60}\n")

    except Exception as e:
        click.echo(f"\n❌ 生成失败: {e}", err=True)
        log.exception("生成用例时发生错误")
        sys.exit(1)


# ... 保留其他命令 (quick, from_swagger, test_connection) ...


def main():
    """入口函数"""
    cli()


if __name__ == '__main__':
    main()