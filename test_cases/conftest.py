"""
Pytest配置文件
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from core.http_client import HTTPClient
from core.file_uploader import FileUploader
from test_data.loader import loader
from test_data.selector import select
from config.settings import config
from utils.logger import log


def pytest_addoption(parser):
    """添加命令行参数"""
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="测试环境: dev, test, prod"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_environment(request):
    """设置测试环境"""
    env = request.config.getoption("--env")
    config.set_environment(env)

    log.info("=" * 60)
    log.info(f"测试环境: {env}")
    log.info(f"API Base URL: {config.api.base_url}")
    log.info("=" * 60)

    yield

    log.info("测试执行完成")


@pytest.fixture(scope="session", autouse=True)
def setup_data_loader(request):
    """初始化数据加载器"""
    env = request.config.getoption("--env")

    # 显示统计
    stats = loader.get_statistics()
    print(f"\n{'=' * 60}")
    print(f"测试数据统计 (环境: {env})")
    print(f"{'=' * 60}")
    print(f"总用例数: {stats['total']}")
    print(f"按优先级: {stats['by_priority']}")
    print(f"按分类: {stats.get('by_category', {})}")
    print(f"{'=' * 60}\n")

    yield

    # 清理
    loader.clear_cache()


@pytest.fixture(scope="session")
def http_client():
    """HTTP客户端fixture"""
    client = HTTPClient()
    yield client
    client.close()


@pytest.fixture(scope="session")
def file_uploader(http_client):
    """文件上传器fixture"""
    return FileUploader(http_client)


@pytest.fixture
def api_client(http_client):
    """API客户端（每个测试独立）"""
    return http_client


@pytest.fixture
def test_selector():
    """测试选择器fixture"""
    return select


# Pytest钩子：动态参数化
def pytest_generate_tests(metafunc):
    """
    根据marker动态参数化

    用法：
    @pytest.mark.load_cases(tags=["smoke"])
    def test_something(test_case):
        pass
    """
    if "test_case" in metafunc.fixturenames:
        marker = metafunc.definition.get_closest_marker("load_cases")

        if marker:
            kwargs = marker.kwargs

            # 使用选择器加载数据
            selector = select()

            if "category" in kwargs:
                selector = selector.from_category(
                    kwargs["category"],
                    kwargs.get("subcategory")
                )

            if "tags" in kwargs:
                selector = selector.with_tags(kwargs["tags"])

            if "priority" in kwargs:
                selector = selector.with_priority(kwargs["priority"])

            if "file" in kwargs:
                selector = selector.from_file(kwargs["file"])

            cases = selector.for_environment().get()

            # 参数化
            if cases:
                ids = [f"{case.id}" for case in cases]
                metafunc.parametrize("test_case", cases, ids=ids)
            else:
                # 无数据时跳过
                current_env = config.get_current_env()
                pytest.skip(f"无可用测试数据 (环境: {current_env})")


def pytest_configure(config):
    """Pytest配置"""
    # 注册自定义markers
    config.addinivalue_line(
        "markers", "load_cases: 动态加载测试数据"
    )