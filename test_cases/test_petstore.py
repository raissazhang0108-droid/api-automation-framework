"""
Petstore API 测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_data.selector import select
from utils.assertions import APIAssertions


class TestPetstoreAPI:
    """Petstore API 测试套件"""

    @pytest.mark.petstore
    @pytest.mark.positive
    @pytest.mark.parametrize(
        "test_case",
        select()
        .from_category("petstore")
        .with_tags(["positive"])
        .for_environment()
        .get()
    )
    def test_positive_cases(self, api_client, test_case):
        """正向测试用例"""
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
        if test_case.expected.response_contains:
            APIAssertions.assert_response_contains(
                response,
                test_case.expected.response_contains
            )

    @pytest.mark.petstore
    @pytest.mark.negative
    @pytest.mark.parametrize(
        "test_case",
        select()
        .from_category("petstore")
        .with_tags(["negative"])
        .for_environment()
        .get()
    )
    def test_negative_cases(self, api_client, test_case):
        """负向测试用例"""
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

        # 断言错误码（如果有）
        if hasattr(test_case.expected, 'error_code') and test_case.expected.error_code:
            APIAssertions.assert_error_response(
                response,
                error_code=test_case.expected.error_code
            )