"""
AI Agent基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from utils.logger import log


class BaseAgent(ABC):
    """AI Agent基类"""

    def __init__(self, model: str = "default"):
        """
        初始化Agent

        Args:
            model: 模型名称
        """
        self.model = model
        self.prompts_dir = Path(__file__).parent.parent / "prompts"

    def load_prompt_template(self, case_type: str) -> str:
        """
        加载提示词模板

        Args:
            case_type: 用例类型（positive/negative/boundary/security）

        Returns:
            提示词模板
        """
        prompt_file = self.prompts_dir / f"{case_type}_cases.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"提示词模板不存在: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()

        log.debug(f"加载提示词模板: {case_type}")
        return template

    @abstractmethod
    def generate_cases(
            self,
            api_spec: Dict[str, Any],
            case_type: str,
            count: int = 10
    ) -> Dict[str, Any]:
        """
        生成测试用例（抽象方法）

        Args:
            api_spec: API规格
            case_type: 用例类型
            count: 生成数量

        Returns:
            生成的测试用例
        """
        pass

    def extract_json(self, text: str) -> str:
        """
        从文本中提取JSON

        Args:
            text: 包含JSON的文本

        Returns:
            纯JSON字符串
        """
        # 去掉markdown代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.rfind("```")
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.rfind("```")
            return text[start:end].strip()

        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            return text[start:end].strip()

        return text.strip()

    def validate_generated_cases(
            self,
            cases: Dict[str, Any]
    ) -> List[str]:
        """
        验证生成的用例

        Args:
            cases: 生成的用例

        Returns:
            问题列表（空列表表示通过）
        """
        issues = []

        if "test_cases" not in cases:
            issues.append("缺少test_cases字段")
            return issues

        test_cases = cases["test_cases"]

        if not isinstance(test_cases, list):
            issues.append("test_cases必须是数组")
            return issues

        if len(test_cases) == 0:
            issues.append("test_cases为空")
            return issues

        # 验证每个用例
        required_fields = ["id", "title", "tags", "api", "data", "expected"]

        for idx, case in enumerate(test_cases):
            case_id = case.get("id", f"第{idx + 1}个用例")

            # 检查必要字段
            for field in required_fields:
                if field not in case:
                    issues.append(f"{case_id}: 缺少{field}字段")

            # 检查tags
            tags = case.get("tags", [])
            if not isinstance(tags, list):
                issues.append(f"{case_id}: tags必须是数组")
            else:
                # 检查是否有测试类型标签
                if not any(t in tags for t in ["positive", "negative", "boundary", "security"]):
                    issues.append(f"{case_id}: 缺少测试类型标签")

                # 检查是否有优先级标签
                if not any(t in tags for t in ["p0", "p1", "p2"]):
                    issues.append(f"{case_id}: 缺少优先级标签")

            # 检查API信息
            api_info = case.get("api", {})
            if "endpoint" not in api_info:
                issues.append(f"{case_id}: 缺少api.endpoint")
            if "method" not in api_info:
                issues.append(f"{case_id}: 缺少api.method")

            # 检查期望结果
            expected = case.get("expected", {})
            if "status_code" not in expected:
                issues.append(f"{case_id}: 缺少expected.status_code")

        return issues

    def format_api_spec(self, api_spec: Dict[str, Any]) -> str:
        """
        格式化API规格为字符串

        Args:
            api_spec: API规格

        Returns:
            格式化的字符串
        """
        return json.dumps(api_spec, indent=2, ensure_ascii=False)