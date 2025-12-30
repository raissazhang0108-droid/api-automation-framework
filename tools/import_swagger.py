#!/usr/bin/env python3
"""
Swagger/OpenAPI导入工具
将Swagger文档转换为API规格文件
"""
import click
import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import log


@click.group()
def cli():
    """Swagger/OpenAPI导入工具"""
    pass


@cli.command()
@click.argument('swagger-file', type=click.Path(exists=True))
@click.option('--output-dir',
              type=click.Path(),
              default='specs',
              help='输出目录')
@click.option('--format',
              type=click.Choice(['json', 'yaml']),
              default='json',
              help='输出格式')
def convert(swagger_file, output_dir, format):
    """
    转换Swagger为API规格文件

    示例：
        python tools/import_swagger.py convert api-docs.json
        python tools/import_swagger.py convert api-docs.yaml --format yaml
    """
    click.echo(f"\n📄 导入Swagger文档: {swagger_file}\n")

    # 加载Swagger
    swagger_path = Path(swagger_file)

    if swagger_path.suffix in ['.yaml', '.yml']:
        with open(swagger_path) as f:
            swagger = yaml.safe_load(f)
    else:
        with open(swagger_path) as f:
            swagger = json.load(f)

    # 解析
    specs = parse_swagger(swagger)

    click.echo(f"发现 {len(specs)} 个API端点\n")

    # 保存
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        # 生成文件名
        name = spec['name'].replace(' ', '_').replace('/', '_')

        if format == 'json':
            file_path = output_path / f"{name}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
        else:
            file_path = output_path / f"{name}.yaml"
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, default_flow_style=False, allow_unicode=True)

        click.echo(f"✅ {spec['name']} -> {file_path}")

    click.echo(f"\n💾 已保存到: {output_path}\n")


@cli.command()
@click.argument('swagger-file', type=click.Path(exists=True))
def analyze(swagger_file):
    """
    分析Swagger文档

    示例：
        python tools/import_swagger.py analyze api-docs.json
    """
    click.echo(f"\n🔍 分析Swagger文档\n")

    # 加载
    swagger_path = Path(swagger_file)

    if swagger_path.suffix in ['.yaml', '.yml']:
        with open(swagger_path) as f:
            swagger = yaml.safe_load(f)
    else:
        with open(swagger_path) as f:
            swagger = json.load(f)

    # 基本信息
    info = swagger.get('info', {})
    click.echo(f"标题: {info.get('title', 'N/A')}")
    click.echo(f"版本: {info.get('version', 'N/A')}")
    click.echo(f"描述: {info.get('description', 'N/A')}\n")

    # 统计
    paths = swagger.get('paths', {})

    total_endpoints = 0
    methods_count = {}

    for path, methods in paths.items():
        for method in methods:
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                total_endpoints += 1
                methods_count[method.upper()] = methods_count.get(method.upper(), 0) + 1

    click.echo(f"端点总数: {total_endpoints}")
    click.echo(f"\n按HTTP方法:")
    for method, count in sorted(methods_count.items()):
        click.echo(f"  {method}: {count}")

    # Tags统计
    all_tags = set()
    for path, methods in paths.items():
        for method, details in methods.items():
            tags = details.get('tags', [])
            all_tags.update(tags)

    if all_tags:
        click.echo(f"\n标签 ({len(all_tags)}):")
        for tag in sorted(all_tags):
            click.echo(f"  - {tag}")

    click.echo()


def parse_swagger(swagger: Dict[str, Any]) -> list:
    """解析Swagger为API规格列表"""
    specs = []

    paths = swagger.get('paths', {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            spec = {
                "name": f"{method.upper()} {path}",
                "endpoint": path,
                "method": method.upper(),
                "summary": details.get('summary', ''),
                "description": details.get('description', ''),
                "tags": details.get('tags', []),
                "parameters": extract_parameters(details),
                "requestBody": extract_request_body(details),
                "responses": extract_responses(details)
            }

            specs.append(spec)

    return specs


def extract_parameters(details: Dict) -> list:
    """提取参数"""
    parameters = []

    for param in details.get('parameters', []):
        parameters.append({
            "name": param.get('name'),
            "in": param.get('in'),
            "required": param.get('required', False),
            "type": param.get('type') or param.get('schema', {}).get('type'),
            "description": param.get('description', '')
        })

    return parameters


def extract_request_body(details: Dict) -> Dict:
    """提取请求体"""
    request_body = details.get('requestBody', {})

    if not request_body:
        return {}

    content = request_body.get('content', {})

    # 提取JSON schema
    json_content = content.get('application/json', {})
    schema = json_content.get('schema', {})

    return {
        "required": request_body.get('required', False),
        "schema": schema
    }


def extract_responses(details: Dict) -> Dict:
    """提取响应"""
    responses = {}

    for status_code, response in details.get('responses', {}).items():
        content = response.get('content', {})
        json_content = content.get('application/json', {})

        responses[status_code] = {
            "description": response.get('description', ''),
            "schema": json_content.get('schema', {})
        }

    return responses


def main():
    """入口函数"""
    cli()


if __name__ == '__main__':
    main()