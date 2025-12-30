"""
测试用例数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Priority(int, Enum):
    """优先级"""
    P0 = 0
    P1 = 1
    P2 = 2


class APIInfo(BaseModel):
    """API信息"""
    endpoint: str
    method: HTTPMethod
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None


class ExpectedResult(BaseModel):
    """期望结果"""
    status_code: int
    response_contains: Optional[List[str]] = None
    response_schema: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TestCase(BaseModel):
    """测试用例模型"""
    id: str
    title: str
    tags: List[str]
    environments: List[str]
    priority: Priority = Priority.P2
    api: APIInfo
    data: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, str]] = None  # 文件上传
    expected: ExpectedResult

    # 元数据
    file_path: Optional[str] = Field(default=None, alias="_file_path")
    file_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="_file_metadata")

    class Config:
        use_enum_values = True


class TestSuiteMetadata(BaseModel):
    """测试套件元数据"""
    file: str
    description: str
    total_cases: int
    tags: List[str]
    last_updated: str


class TestSuite(BaseModel):
    """测试套件"""
    metadata: TestSuiteMetadata
    test_cases: List[TestCase]