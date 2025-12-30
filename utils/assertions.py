"""
通用断言工具
"""
from typing import Any, List, Dict, Optional
import json
from utils.logger import log


class APIAssertions:
    """API测试断言"""

    @staticmethod
    def assert_status_code(response, expected_code: int, message: str = ""):
        """断言状态码"""
        actual_code = response.status_code
        assert_message = message or f"期望状态码 {expected_code}, 实际 {actual_code}"

        try:
            assert actual_code == expected_code, assert_message
            log.info(f"✓ 状态码断言通过: {actual_code}")
        except AssertionError as e:
            log.error(f"✗ 状态码断言失败: {e}")
            log.error(f"响应内容: {response.text[:500]}")
            raise

    @staticmethod
    def assert_response_time(duration: float, max_time: float):
        """断言响应时间"""
        assert duration <= max_time, f"响应时间 {duration}s 超过限制 {max_time}s"
        log.info(f"✓ 响应时间断言通过: {duration}s <= {max_time}s")

    @staticmethod
    def assert_response_contains(response, fields: List[str]):
        """断言响应包含指定字段"""
        try:
            response_json = response.json()
        except:
            raise AssertionError("响应不是有效的JSON格式")

        missing_fields = []
        for field in fields:
            if field not in response_json:
                missing_fields.append(field)

        if missing_fields:
            raise AssertionError(f"响应缺少字段: {missing_fields}")

        log.info(f"✓ 响应字段断言通过: {fields}")

    @staticmethod
    def assert_json_match(response, expected: Dict[str, Any], partial: bool = True):
        """断言JSON匹配"""
        try:
            actual = response.json()
        except:
            raise AssertionError("响应不是有效的JSON格式")

        if partial:
            # 部分匹配
            for key, value in expected.items():
                if key not in actual:
                    raise AssertionError(f"响应缺少键: {key}")
                if actual[key] != value:
                    raise AssertionError(
                        f"键 {key} 值不匹配: 期望 {value}, 实际 {actual[key]}"
                    )
        else:
            # 完全匹配
            if actual != expected:
                raise AssertionError(
                    f"JSON不匹配:\n期望: {json.dumps(expected, indent=2)}\n实际: {json.dumps(actual, indent=2)}"
                )

        log.info("✓ JSON匹配断言通过")

    @staticmethod
    def assert_error_response(response, error_code: str = None, error_message: str = None):
        """断言错误响应"""
        try:
            error_json = response.json()
        except:
            raise AssertionError("错误响应不是有效的JSON格式")

        if error_code:
            actual_code = error_json.get("error_code") or error_json.get("code")
            assert actual_code == error_code, f"错误码不匹配: 期望 {error_code}, 实际 {actual_code}"

        if error_message:
            actual_message = error_json.get("error_message") or error_json.get("message")
            assert error_message in actual_message, f"错误信息不匹配: 期望包含 '{error_message}', 实际 '{actual_message}'"

        log.info("✓ 错误响应断言通过")

    @staticmethod
    def assert_schema(response, schema: Dict[str, Any]):
        """断言响应符合Schema"""
        from jsonschema import validate, ValidationError

        try:
            response_json = response.json()
            validate(instance=response_json, schema=schema)
            log.info("✓ Schema验证通过")
        except ValidationError as e:
            raise AssertionError(f"Schema验证失败: {e.message}")


# 便捷函数
def assert_success(response):
    """断言成功响应（2xx）"""
    APIAssertions.assert_status_code(response, 200)


def assert_created(response):
    """断言创建成功（201）"""
    APIAssertions.assert_status_code(response, 201)


def assert_bad_request(response):
    """断言错误请求（400）"""
    APIAssertions.assert_status_code(response, 400)


def assert_unauthorized(response):
    """断言未授权（401）"""
    APIAssertions.assert_status_code(response, 401)


def assert_forbidden(response):
    """断言禁止访问（403）"""
    APIAssertions.assert_status_code(response, 403)


def assert_not_found(response):
    """断言未找到（404）"""
    APIAssertions.assert_status_code(response, 404)