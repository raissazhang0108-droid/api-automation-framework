"""
AI Agent基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path
import json
import re


class BaseAgent(ABC):
    """AI Agent基类"""

    def __init__(self, model: str = "default"):
        self.model = model
        self.prompts_dir = Path(__file__).parent.parent / "prompts"

    def load_prompt_template(self, case_type: str) -> str:
        """加载提示词模板"""
        prompt_file = self.prompts_dir / f"{case_type}_cases.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"提示词模板不存在: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()

    @abstractmethod
    def generate_cases(
            self,
            api_spec: Dict[str, Any],
            case_type: str,
            count: int = 10
    ) -> Dict[str, Any]:
        """生成测试用例（抽象方法）"""
        pass

    @abstractmethod
    def generate_raw(self, prompt: str) -> str:
        """
        生成原始文本响应

        Args:
            prompt: 提示词

        Returns:
            AI生成的原始文本
        """
        pass

    def extract_json(self, text: str) -> str:
        """
        从文本中提取JSON（增强版）
        支持从包含markdown、注释等额外内容的文本中提取纯JSON
        """
        text = text.strip()

        # 方法1: 移除markdown代码块
        if "```json" in text:
            pattern = r'```json\s*(.*?)\s*```'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                text = matches[0].strip()
        elif "```" in text:
            pattern = r'```\s*(.*?)\s*```'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                text = matches[0].strip()

        # 方法2: 查找第一个 { 到匹配的 }
        first_brace = text.find("{")

        if first_brace == -1:
            raise ValueError("未找到JSON对象")

        # 从第一个 { 开始计数括号，找到完整的JSON对象
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i in range(first_brace, len(text)):
            char = text[i]

            # 处理字符串中的引号
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            # 只在字符串外计数括号
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

        if json_end > first_brace:
            json_text = text[first_brace:json_end]

            # 验证JSON是否有效
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError as e:
                # 如果解析失败，尝试查找问题
                raise ValueError(f"提取的JSON无效: {e}")

        # 方法3: 如果上面都失败，尝试简单的方式
        last_brace = text.rfind("}")
        if last_brace > first_brace:
            json_text = text[first_brace:last_brace + 1]
            try:
                json.loads(json_text)
                return json_text
            except:
                pass

        raise ValueError("无法从文本中提取有效的JSON")

    def validate_generated_cases(self, cases: Dict[str, Any]) -> List[str]:
        """验证生成的用例"""
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

        # 验证每个用例的必需字段
        required_fields = ["id", "title", "tags", "api", "data", "expected"]

        for idx, case in enumerate(test_cases):
            for field in required_fields:
                if field not in case:
                    issues.append(f"用例 {idx + 1} 缺少必需字段: {field}")

        return issues

    def format_api_spec(self, api_spec: Dict[str, Any]) -> str:
        """格式化API规格"""
        return json.dumps(api_spec, indent=2, ensure_ascii=False)


