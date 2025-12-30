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
def generate(provider, model, api_key, spec_file, type, count, output, output_dir):
    """
    生成测试用例

    示例：
        # 使用OpenAI生成正向用例
        python tools/generate_cases.py generate --provider openai --spec-file specs/patient.json --type positive --count 10

        # 使用Ollama生成完整测试套件
        python tools/generate_cases.py generate --provider ollama --model llama3.2 --spec-file specs/patient.json --type all

        # 使用DeepSeek生成负向用例
        python tools/generate_cases.py generate --provider deepseek --spec-file specs/patient.json --type negative
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

        # 保存文件
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            spec_name = Path(spec_file).stem
            output = f"{spec_name}_{type}_{timestamp}.json"

        output_path = Path(output_dir) / output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        click.echo(f"\n💾 已保存到: {output_path}")

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


@cli.command()
@click.option('--provider',
              type=click.Choice(['openai', 'ollama', 'deepseek']),
              default='openai',
              help='AI提供商')
@click.option('--model', help='模型名称')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='API密钥')
@click.argument('description')
@click.option('--output-dir',
              type=click.Path(),
              default='test_data/ai_generated',
              help='输出目录')
def quick(provider, model, api_key, description, output_dir):
    """
    快速生成（自然语言描述）

    示例：
        python tools/generate_cases.py quick "测试患者注册API，包括正常和异常场景"
    """
    click.echo(f"\n🚀 快速生成模式")
    click.echo(f"描述: {description}\n")

    # 简化的API规格
    api_spec = {
        "description": description,
        "endpoint": "/api/v1/resource",
        "method": "POST"
    }

    # 创建生成器
    try:
        generator = create_generator(
            provider=provider,
            model=model,
            api_key=api_key
        )
    except Exception as e:
        click.echo(f"❌ 初始化失败: {e}", err=True)
        sys.exit(1)

    # 生成完整套件
    click.echo("生成完整测试套件...")

    try:
        with click.progressbar(length=1, label='生成中') as bar:
            result = generator.generate_suite(api_spec)
            bar.update(1)

        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"quick_gen_{timestamp}.json"
        output_path = Path(output_dir) / output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        total = len(result['test_cases'])
        click.echo(f"\n✅ 已生成 {total} 个用例")
        click.echo(f"💾 保存位置: {output_path}\n")

    except Exception as e:
        click.echo(f"❌ 生成失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--provider',
              type=click.Choice(['openai', 'ollama', 'deepseek']),
              default='openai')
@click.option('--model', help='模型名称')
@click.option('--api-key', envvar='OPENAI_API_KEY')
@click.option('--swagger-file',
              type=click.Path(exists=True),
              required=True,
              help='Swagger/OpenAPI文件')
@click.option('--output-dir',
              type=click.Path(),
              default='test_data/ai_generated/from_swagger',
              help='输出目录')
@click.option('--batch-size', default=5, help='批量处理大小')
def from_swagger(provider, model, api_key, swagger_file, output_dir, batch_size):
    """
    从Swagger/OpenAPI规格批量生成

    示例：
        python tools/generate_cases.py from-swagger --swagger-file api-docs.json
    """
    click.echo(f"\n📋 从Swagger生成测试用例")
    click.echo(f"文件: {swagger_file}\n")

    # 加载Swagger
    with open(swagger_file) as f:
        swagger = json.load(f)

    paths = swagger.get("paths", {})
    click.echo(f"发现 {len(paths)} 个API端点\n")

    # 创建生成器
    try:
        generator = create_generator(
            provider=provider,
            model=model,
            api_key=api_key
        )
    except Exception as e:
        click.echo(f"❌ 初始化失败: {e}", err=True)
        sys.exit(1)

    # 准备生成任务
    tasks = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            summary = details.get("summary", path)

            api_spec = {
                "endpoint": path,
                "method": method.upper(),
                "summary": summary,
                "parameters": details.get("parameters", []),
                "requestBody": details.get("requestBody", {}),
                "responses": details.get("responses", {})
            }

            tasks.append({
                "name": f"{method.upper()} {path}",
                "spec": api_spec
            })

    click.echo(f"将生成 {len(tasks)} 组测试用例\n")

    if not click.confirm("继续？", default=True):
        return

    # 批量生成
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failed_tasks = []

    with click.progressbar(
            tasks,
            label='批量生成中',
            show_pos=True
    ) as bar:
        for task in bar:
            try:
                result = generator.generate_suite(task["spec"])

                # 保存
                filename = task["name"].replace("/", "_").replace(" ", "_") + ".json"
                file_path = output_path / filename

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                success_count += 1

            except Exception as e:
                log.error(f"生成失败 {task['name']}: {e}")
                failed_tasks.append(task["name"])

    # 显示结果
    click.echo(f"\n✅ 成功: {success_count}/{len(tasks)}")

    if failed_tasks:
        click.echo(f"\n❌ 失败的任务:")
        for task_name in failed_tasks:
            click.echo(f"   - {task_name}")

    click.echo(f"\n💾 保存目录: {output_path}\n")


@cli.command()
def test_connection():
    """测试AI服务连接"""
    click.echo("\n🔍 测试AI服务连接...\n")

    # 测试OpenAI
    click.echo("1. OpenAI")
    try:
        from config.settings import config
        if config.settings.openai_api_key:
            generator = create_generator('openai')
            click.echo("   ✅ 连接成功")
        else:
            click.echo("   ⚠️  未配置API Key")
    except Exception as e:
        click.echo(f"   ❌ 连接失败: {e}")

    # 测试Ollama
    click.echo("\n2. Ollama")
    try:
        generator = create_generator('ollama')
        click.echo("   ✅ 连接成功")
    except Exception as e:
        click.echo(f"   ❌ 连接失败: {e}")
        click.echo("   💡 启动命令: ollama serve")

    # 测试DeepSeek
    click.echo("\n3. DeepSeek")
    try:
        from config.settings import config
        if config.settings.deepseek_api_key:
            generator = create_generator('deepseek')
            click.echo("   ✅ 连接成功")
        else:
            click.echo("   ⚠️  未配置API Key")
    except Exception as e:
        click.echo(f"   ❌ 连接失败: {e}")

    click.echo()


def main():
    """入口函数"""
    cli()


if __name__ == '__main__':
    main()