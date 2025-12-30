"""
测试数据加载器
支持多环境、缓存、智能过滤
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from functools import lru_cache

from config.settings import config
from models.test_case_model import TestCase, TestSuite
from utils.logger import log


class TestDataLoader:
    """
    测试数据加载器

    特性：
    - 按环境加载数据
    - 自动构建索引
    - 支持缓存
    - 智能过滤
    - 数据验证
    """

    def __init__(self):
        self._file_cache: Dict[str, Dict] = {}
        self._case_index: Optional[Dict[str, TestCase]] = None
        self._current_env = config.get_current_env()

    @property
    def data_path(self) -> Path:
        """获取当前环境的数据目录"""
        return config.data_path

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        加载JSON文件（带缓存）

        Args:
            file_path: 文件路径

        Returns:
            JSON数据
        """
        cache_key = str(file_path)

        # 检查缓存
        if cache_key in self._file_cache:
            log.debug(f"从缓存加载: {file_path.name}")
            return self._file_cache[cache_key]

        # 加载文件
        if not file_path.exists():
            log.warning(f"文件不存在: {file_path}")
            return {"metadata": {}, "test_cases": []}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            log.debug(f"加载文件: {file_path.name}")

            # 缓存
            self._file_cache[cache_key] = data

            return data

        except json.JSONDecodeError as e:
            log.error(f"JSON解析失败 {file_path}: {e}")
            return {"metadata": {}, "test_cases": []}
        except Exception as e:
            log.error(f"加载文件失败 {file_path}: {e}")
            return {"metadata": {}, "test_cases": []}

    def _parse_test_case(self, case_data: Dict[str, Any], file_path: Path) -> TestCase:
        """
        解析测试用例

        Args:
            case_data: 用例数据
            file_path: 文件路径

        Returns:
            TestCase对象
        """
        # 添加文件路径信息
        case_data["_file_path"] = str(file_path.relative_to(self.data_path.parent))

        try:
            return TestCase(**case_data)
        except Exception as e:
            log.error(f"解析测试用例失败: {e}")
            log.error(f"数据: {case_data}")
            raise

    def _build_case_index(self) -> Dict[str, TestCase]:
        """
        构建测试用例索引

        Returns:
            {case_id: TestCase} 映射
        """
        if self._case_index is not None:
            return self._case_index

        log.info(f"构建测试用例索引 (环境: {self._current_env})...")

        index = {}

        # 遍历所有JSON文件
        json_files = list(self.data_path.rglob("*.json"))
        log.info(f"找到 {len(json_files)} 个JSON文件")

        for json_file in json_files:
            data = self._load_json_file(json_file)

            test_cases = data.get("test_cases", [])

            for case_data in test_cases:
                case_id = case_data.get("id")

                if not case_id:
                    log.warning(f"用例缺少ID: {json_file}")
                    continue

                if case_id in index:
                    log.warning(f"重复的用例ID: {case_id}")

                # 解析用例
                try:
                    test_case = self._parse_test_case(case_data, json_file)
                    index[case_id] = test_case
                except Exception as e:
                    log.error(f"跳过无效用例 {case_id}: {e}")

        log.info(f"索引构建完成，共 {len(index)} 个测试用例")

        self._case_index = index
        return index

    def get_all_cases(self) -> List[TestCase]:
        """
        获取所有测试用例

        Returns:
            测试用例列表
        """
        index = self._build_case_index()
        return list(index.values())

    def get_case_by_id(self, case_id: str) -> Optional[TestCase]:
        """
        根据ID获取测试用例

        Args:
            case_id: 用例ID

        Returns:
            TestCase对象或None
        """
        index = self._build_case_index()
        return index.get(case_id)

    def get_cases_by_file(self, relative_path: str) -> List[TestCase]:
        """
        从指定文件加载测试用例

        Args:
            relative_path: 相对路径，如 "patients/registration/positive.json"

        Returns:
            测试用例列表
        """
        file_path = self.data_path / relative_path

        if not file_path.exists():
            log.warning(f"文件不存在: {file_path}")
            return []

        data = self._load_json_file(file_path)
        test_cases = []

        for case_data in data.get("test_cases", []):
            try:
                test_case = self._parse_test_case(case_data, file_path)
                test_cases.append(test_case)
            except Exception as e:
                log.error(f"解析用例失败: {e}")

        log.info(f"从文件加载 {len(test_cases)} 个用例: {relative_path}")

        return test_cases

    def get_cases_by_category(
            self,
            category: str,
            subcategory: Optional[str] = None
    ) -> List[TestCase]:
        """
        按分类加载测试用例

        Args:
            category: 主分类（如 'patients', 'diagnosis'）
            subcategory: 子分类（如 'registration', 'update'）

        Returns:
            测试用例列表

        Examples:
            get_cases_by_category("patients")  # 所有患者相关用例
            get_cases_by_category("patients", "registration")  # 只要注册用例
        """
        if subcategory:
            search_path = self.data_path / category / subcategory
        else:
            search_path = self.data_path / category

        if not search_path.exists():
            log.warning(f"路径不存在: {search_path}")
            return []

        test_cases = []
        json_files = list(search_path.rglob("*.json"))

        for json_file in json_files:
            data = self._load_json_file(json_file)

            for case_data in data.get("test_cases", []):
                try:
                    test_case = self._parse_test_case(case_data, json_file)
                    test_cases.append(test_case)
                except Exception as e:
                    log.error(f"解析用例失败: {e}")

        log.info(
            f"从分类加载 {len(test_cases)} 个用例: "
            f"{category}/{subcategory or '*'}"
        )

        return test_cases

    def get_cases_by_tags(
            self,
            tags: List[str],
            match_all: bool = False
    ) -> List[TestCase]:
        """
        按标签过滤测试用例

        Args:
            tags: 标签列表
            match_all: True=必须匹配所有标签，False=匹配任一标签

        Returns:
            测试用例列表

        Examples:
            get_cases_by_tags(["smoke"])  # 冒烟测试
            get_cases_by_tags(["p0", "patients"])  # P0的患者用例
            get_cases_by_tags(["positive", "p0"], match_all=True)  # 必须同时有两个标签
        """
        all_cases = self.get_all_cases()

        filtered = []
        for case in all_cases:
            case_tags = case.tags

            if match_all:
                # 必须包含所有指定标签
                if all(tag in case_tags for tag in tags):
                    filtered.append(case)
            else:
                # 包含任一标签即可
                if any(tag in case_tags for tag in tags):
                    filtered.append(case)

        log.info(
            f"标签过滤 {tags} ({'AND' if match_all else 'OR'}): "
            f"{len(filtered)} 个用例"
        )

        return filtered

    def get_cases_by_priority(self, max_priority: int) -> List[TestCase]:
        """
        按优先级过滤

        Args:
            max_priority: 最大优先级（0=P0, 1=P1, 2=P2）
                         例如 max_priority=1 会返回P0和P1的用例

        Returns:
            测试用例列表
        """
        all_cases = self.get_all_cases()

        filtered = [
            case for case in all_cases
            if case.priority <= max_priority
        ]

        log.info(f"优先级 ≤P{max_priority}: {len(filtered)} 个用例")

        return filtered

    def get_cases_by_environment(
            self,
            env: Optional[str] = None
    ) -> List[TestCase]:
        """
        按环境过滤（只返回当前环境支持的用例）

        Args:
            env: 环境名称（默认使用当前环境）

        Returns:
            测试用例列表
        """
        target_env = env or self._current_env
        all_cases = self.get_all_cases()

        filtered = [
            case for case in all_cases
            if target_env in case.environments
        ]

        log.info(f"环境过滤 {target_env}: {len(filtered)} 个用例")

        return filtered

    def filter_cases(
            self,
            cases: List[TestCase],
            predicate: Callable[[TestCase], bool]
    ) -> List[TestCase]:
        """
        自定义过滤条件

        Args:
            cases: 待过滤的用例列表
            predicate: 过滤函数，返回True保留，False丢弃

        Returns:
            过滤后的用例列表

        Example:
            # 过滤出POST请求的用例
            loader.filter_cases(
                cases,
                lambda c: c.api.method == "POST"
            )
        """
        filtered = [case for case in cases if predicate(case)]
        log.info(f"自定义过滤: {len(filtered)}/{len(cases)} 个用例")
        return filtered

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取测试用例统计信息

        Returns:
            统计数据字典
        """
        all_cases = self.get_all_cases()

        stats = {
            "total": len(all_cases),
            "environment": self._current_env,
            "by_priority": {},
            "by_tags": {},
            "by_category": {},
            "by_method": {},
            "by_environment": {}
        }

        # 按优先级统计
        for case in all_cases:
            priority = f"P{case.priority}"
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

        # 按标签统计
        for case in all_cases:
            for tag in case.tags:
                stats["by_tags"][tag] = stats["by_tags"].get(tag, 0) + 1

        # 按分类统计（从文件路径推断）
        for case in all_cases:
            if case.file_path:
                # test_data/dev/patients/... -> patients
                parts = Path(case.file_path).parts
                if len(parts) >= 3:
                    category = parts[2]
                    stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        # 按HTTP方法统计
        for case in all_cases:
            method = case.api.method.value
            stats["by_method"][method] = stats["by_method"].get(method, 0) + 1

        # 按环境统计
        for case in all_cases:
            for env in case.environments:
                stats["by_environment"][env] = stats["by_environment"].get(env, 0) + 1

        return stats

    def validate_data_availability(self, test_case: TestCase) -> bool:
        """
        验证测试用例在当前环境是否有数据

        Args:
            test_case: 测试用例

        Returns:
            True=有数据，False=无数据
        """
        current_env = self._current_env

        if current_env not in test_case.environments:
            log.warning(
                f"用例 {test_case.id} 在环境 {current_env} 无数据，"
                f"支持的环境: {test_case.environments}"
            )
            return False

        return True

    def clear_cache(self):
        """清除缓存"""
        self._file_cache.clear()
        self._case_index = None
        log.info("数据缓存已清除")

    def reload(self):
        """重新加载数据"""
        log.info("重新加载测试数据...")
        self.clear_cache()
        self._build_case_index()


# 全局加载器实例
loader = TestDataLoader()


# 便捷函数
def load_all() -> List[TestCase]:
    """加载所有用例"""
    return loader.get_all_cases()


def load_by_tags(*tags: str) -> List[TestCase]:
    """按标签加载"""
    return loader.get_cases_by_tags(list(tags))


def load_by_category(category: str, subcategory: Optional[str] = None) -> List[TestCase]:
    """按分类加载"""
    return loader.get_cases_by_category(category, subcategory)


def load_by_file(file_path: str) -> List[TestCase]:
    """从文件加载"""
    return loader.get_cases_by_file(file_path)


def load_smoke_tests() -> List[TestCase]:
    """加载冒烟测试"""
    return loader.get_cases_by_tags(["smoke"])


def load_p0_tests() -> List[TestCase]:
    """加载P0用例"""
    return loader.get_cases_by_priority(0)