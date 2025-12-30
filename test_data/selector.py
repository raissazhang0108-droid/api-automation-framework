"""
测试用例选择器
支持链式调用的流式API
"""
from typing import List, Callable, Optional
from models.test_case_model import TestCase, HTTPMethod
from test_data.loader import loader
from utils.logger import log


class TestCaseSelector:
    """
    测试用例选择器（支持链式调用）

    Example:
        TestCaseSelector()
            .from_category("patients")
            .with_tags(["smoke"])
            .for_environment()
            .with_priority(0)
            .with_method("POST")
            .get()
    """

    def __init__(self, cases: Optional[List[TestCase]] = None):
        """
        初始化选择器

        Args:
            cases: 初始用例列表（默认加载所有）
        """
        self._cases = cases if cases is not None else loader.get_all_cases()
        self._original_count = len(self._cases)

    def from_all(self) -> 'TestCaseSelector':
        """从所有用例开始"""
        self._cases = loader.get_all_cases()
        return self

    def from_category(
            self,
            category: str,
            subcategory: Optional[str] = None
    ) -> 'TestCaseSelector':
        """
        从指定分类加载

        Args:
            category: 主分类
            subcategory: 子分类

        Returns:
            self（支持链式调用）
        """
        self._cases = loader.get_cases_by_category(category, subcategory)
        return self

    def from_file(self, relative_path: str) -> 'TestCaseSelector':
        """
        从指定文件加载

        Args:
            relative_path: 相对路径

        Returns:
            self
        """
        self._cases = loader.get_cases_by_file(relative_path)
        return self

    def with_tags(
            self,
            tags: List[str],
            match_all: bool = False
    ) -> 'TestCaseSelector':
        """
        按标签过滤

        Args:
            tags: 标签列表
            match_all: 是否必须匹配所有标签

        Returns:
            self
        """
        filtered = []
        for case in self._cases:
            case_tags = case.tags

            if match_all:
                if all(tag in case_tags for tag in tags):
                    filtered.append(case)
            else:
                if any(tag in case_tags for tag in tags):
                    filtered.append(case)

        self._cases = filtered
        log.debug(f"标签过滤后: {len(self._cases)} 个用例")
        return self

    def with_priority(self, max_priority: int) -> 'TestCaseSelector':
        """
        按优先级过滤

        Args:
            max_priority: 最大优先级（0-2）

        Returns:
            self
        """
        self._cases = [
            case for case in self._cases
            if case.priority <= max_priority
        ]
        log.debug(f"优先级过滤后: {len(self._cases)} 个用例")
        return self

    def for_environment(self, env: Optional[str] = None) -> 'TestCaseSelector':
        """
        按环境过滤

        Args:
            env: 环境名称（默认当前环境）

        Returns:
            self
        """
        from config.settings import config

        target_env = env or config.get_current_env()

        self._cases = [
            case for case in self._cases
            if target_env in case.environments
        ]
        log.debug(f"环境过滤后: {len(self._cases)} 个用例")
        return self

    def with_method(self, method: str) -> 'TestCaseSelector':
        """
        按HTTP方法过滤

        Args:
            method: HTTP方法（GET/POST/PUT/DELETE/PATCH）

        Returns:
            self
        """
        method = method.upper()
        self._cases = [
            case for case in self._cases
            if case.api.method.value == method
        ]
        log.debug(f"方法过滤后: {len(self._cases)} 个用例")
        return self

    def with_endpoint(self, endpoint_pattern: str) -> 'TestCaseSelector':
        """
        按API端点过滤

        Args:
            endpoint_pattern: 端点匹配模式（包含匹配）

        Returns:
            self
        """
        self._cases = [
            case for case in self._cases
            if endpoint_pattern in case.api.endpoint
        ]
        log.debug(f"端点过滤后: {len(self._cases)} 个用例")
        return self

    def where(self, predicate: Callable[[TestCase], bool]) -> 'TestCaseSelector':
        """
        自定义过滤条件

        Args:
            predicate: 过滤函数

        Returns:
            self

        Example:
            .where(lambda c: c.data and c.data.get("age", 0) < 18)
        """
        self._cases = [case for case in self._cases if predicate(case)]
        log.debug(f"自定义过滤后: {len(self._cases)} 个用例")
        return self

    def exclude_tags(self, tags: List[str]) -> 'TestCaseSelector':
        """
        排除指定标签

        Args:
            tags: 要排除的标签列表

        Returns:
            self
        """
        self._cases = [
            case for case in self._cases
            if not any(tag in case.tags for tag in tags)
        ]
        log.debug(f"排除标签后: {len(self._cases)} 个用例")
        return self

    def limit(self, n: int) -> 'TestCaseSelector':
        """
        限制数量

        Args:
            n: 最大数量

        Returns:
            self
        """
        self._cases = self._cases[:n]
        log.debug(f"限制数量: {len(self._cases)} 个用例")
        return self

    def sort_by_priority(self, reverse: bool = False) -> 'TestCaseSelector':
        """
        按优先级排序

        Args:
            reverse: 是否倒序

        Returns:
            self
        """
        self._cases = sorted(
            self._cases,
            key=lambda c: c.priority,
            reverse=reverse
        )
        return self

    def sort_by_id(self, reverse: bool = False) -> 'TestCaseSelector':
        """
        按ID排序

        Args:
            reverse: 是否倒序

        Returns:
            self
        """
        self._cases = sorted(
            self._cases,
            key=lambda c: c.id,
            reverse=reverse
        )
        return self

    def get(self) -> List[TestCase]:
        """
        获取结果

        Returns:
            过滤后的用例列表
        """
        log.info(
            f"选择器结果: {len(self._cases)}/{self._original_count} 个用例"
        )
        return self._cases

    def first(self) -> Optional[TestCase]:
        """
        获取第一个

        Returns:
            第一个用例或None
        """
        return self._cases[0] if self._cases else None

    def count(self) -> int:
        """
        获取数量

        Returns:
            用例数量
        """
        return len(self._cases)

    def ids(self) -> List[str]:
        """
        获取所有ID

        Returns:
            ID列表
        """
        return [case.id for case in self._cases]

    def print_summary(self):
        """打印摘要"""
        print(f"\n{'=' * 60}")
        print(f"测试用例选择器 - 摘要")
        print(f"{'=' * 60}")
        print(f"总数: {len(self._cases)}/{self._original_count}")

        if self._cases:
            # 按优先级统计
            by_priority = {}
            for case in self._cases:
                p = f"P{case.priority}"
                by_priority[p] = by_priority.get(p, 0) + 1

            print(f"\n按优先级:")
            for p, count in sorted(by_priority.items()):
                print(f"  {p}: {count}")

            # 按标签统计（Top 5）
            by_tag = {}
            for case in self._cases:
                for tag in case.tags:
                    by_tag[tag] = by_tag.get(tag, 0) + 1

            print(f"\n按标签 (Top 5):")
            for tag, count in sorted(by_tag.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {tag}: {count}")

        print(f"{'=' * 60}\n")


# 便捷函数
def select() -> TestCaseSelector:
    """创建选择器"""
    return TestCaseSelector()