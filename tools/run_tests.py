#!/usr/bin/env python3
"""
测试执行工具
支持多环境、多模式运行
"""
import click
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import config
from test_data.loader import loader


@click.group()
def cli():
    """测试执行工具"""
    pass


@cli.command()
@click.option('--env',
              type=click.Choice(['dev', 'test', 'prod']),
              default='dev',
              help='测试环境')
@click.option('--markers', '-m', help='Pytest markers (如: smoke, p0)')
@click.option('--parallel', '-n', default=1, help='并行进程数 (auto=自动检测)')
@click.option('--reruns', default=0, help='失败重试次数')
@click.option('--html-report/--no-html-report', default=True, help='生成HTML报告')
@click.option('--allure/--no-allure', default=True, help='生成Allure报告')
@click.option('--verbose', '-v', count=True, help='详细输出级别')
def run(env, markers, parallel, reruns, html_report, allure, verbose):
    """
    运行测试

    示例：
        # 运行开发环境所有测试
        python tools/run_tests.py run --env dev

        # 运行冒烟测试（并行4进程）
        python tools/run_tests.py run --env test -m smoke -n 4

        # 运行P0用例（失败重试2次）
        python tools/run_tests.py run --env test -m p0 --reruns 2
    """
    click.echo(f"\n{'=' * 60}")
    click.echo(f"API自动化测试")
    click.echo(f"{'=' * 60}\n")

    # 设置环境
    config.set_environment(env)

    # 显示统计
    stats = loader.get_statistics()
    click.echo(f"环境: {env}")
    click.echo(f"可用用例: {stats['total']}")
    if markers:
        click.echo(f"过滤条件: {markers}")
    click.echo()

    # 构建pytest命令
    cmd = ["pytest"]

    # 环境参数
    cmd.extend(["--env", env])

    # Markers
    if markers:
        cmd.extend(["-m", markers])

    # 并行
    if parallel != 1:
        if parallel == 'auto':
            cmd.extend(["-n", "auto"])
        else:
            cmd.extend(["-n", str(parallel)])

    # 重试
    if reruns > 0:
        cmd.extend(["--reruns", str(reruns)])

    # HTML报告
    if html_report:
        cmd.extend([
            "--html=reports/html/report.html",
            "--self-contained-html"
        ])

    # Allure
    if allure:
        cmd.extend([
            "--alluredir=reports/allure-results",
            "--clean-alluredir"
        ])

    # 详细级别
    if verbose:
        cmd.append("-" + "v" * verbose)

    # 显示命令
    click.echo(f"执行命令: {' '.join(cmd)}\n")
    click.echo(f"{'=' * 60}\n")

    # 执行
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  测试被中断")
        sys.exit(1)


@cli.command()
@click.option('--env',
              type=click.Choice(['dev', 'test', 'prod']),
              default='test')
def smoke(env):
    """运行冒烟测试"""
    click.echo("\n🔥 运行冒烟测试\n")

    cmd = [
        "pytest",
        "--env", env,
        "-m", "smoke",
        "-n", "auto",
        "--tb=short",
        "--maxfail=5"
    ]

    subprocess.run(cmd)


@cli.command()
@click.option('--env', default='test')
def regression(env):
    """运行回归测试"""
    click.echo("\n🔄 运行回归测试\n")

    cmd = [
        "pytest",
        "--env", env,
        "-m", "regression",
        "-n", "auto",
        "--reruns", "1"
    ]

    subprocess.run(cmd)


@cli.command()
@click.option('--env', default='test')
@click.option('--category', required=True, help='模块分类（如: patients, diagnosis）')
def by_module(env, category):
    """按模块运行测试"""
    click.echo(f"\n📦 运行 {category} 模块测试\n")

    cmd = [
        "pytest",
        "--env", env,
        "-m", category,
        "-v"
    ]

    subprocess.run(cmd)


@cli.command()
@click.option('--env', default='test')
@click.option('--priority',
              type=click.Choice(['0', '1', '2']),
              required=True)
def by_priority(env, priority):
    """按优先级运行测试"""
    click.echo(f"\n⭐ 运行 P{priority} 用例\n")

    cmd = [
        "pytest",
        "--env", env,
        "-m", f"p{priority}",
        "-v"
    ]

    subprocess.run(cmd)


@cli.command()
def show_report():
    """显示Allure报告"""
    click.echo("\n📊 生成Allure报告...\n")

    allure_dir = Path("reports/allure-results")

    if not allure_dir.exists() or not list(allure_dir.iterdir()):
        click.echo("❌ 没有找到Allure结果文件")
        click.echo("请先运行测试生成报告")
        return

    cmd = ["allure", "serve", str(allure_dir)]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        click.echo("❌ 未安装Allure")
        click.echo("\n安装方法:")
        click.echo("  macOS: brew install allure")
        click.echo("  Linux: sudo apt-get install allure")
        click.echo("  Windows: scoop install allure")


@cli.command()
def list_cases():
    """列出所有测试用例"""
    click.echo("\n📋 测试用例列表\n")

    cmd = [
        "pytest",
        "--collect-only",
        "-q"
    ]

    subprocess.run(cmd)


@cli.command()
@click.option('--env', default='dev')
def stats(env):
    """显示测试数据统计"""
    config.set_environment(env)

    stats = loader.get_statistics()

    click.echo(f"\n{'=' * 60}")
    click.echo(f"测试数据统计 - {env} 环境")
    click.echo(f"{'=' * 60}\n")

    click.echo(f"总用例数: {stats['total']}\n")

    click.echo("按优先级:")
    for priority, count in sorted(stats['by_priority'].items()):
        click.echo(f"  {priority}: {count}")

    click.echo("\n按分类:")
    for category, count in sorted(stats['by_category'].items()):
        click.echo(f"  {category}: {count}")

    click.echo("\n按HTTP方法:")
    for method, count in sorted(stats['by_method'].items()):
        click.echo(f"  {method}: {count}")

    click.echo("\n按标签 (Top 10):")
    sorted_tags = sorted(
        stats['by_tags'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for tag, count in sorted_tags:
        click.echo(f"  {tag}: {count}")

    click.echo(f"\n{'=' * 60}\n")


def main():
    """入口函数"""
    cli()


if __name__ == '__main__':
    main()