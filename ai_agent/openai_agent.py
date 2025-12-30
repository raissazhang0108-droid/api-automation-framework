"""
OpenAI Agent实现
"""
from typing import Dict, Any
import json
from openai import OpenAI

from ai_agent.base_agent import BaseAgent
from config.settings import config
from utils.logger import log


class OpenAIAgent(BaseAgent):
    """
    OpenAI Agent
    使用OpenAI API生成测试用例
    """

    def __init__(self, model: str = None, api_key: str = None):
        """
        初始化OpenAI Agent

        Args:
            model: 模型名称（默认从配置读取）
            api_key: API密钥（默认从配置读取）
        """
        model = model or config.settings.openai_model
        super().__init__(model)

        api_key = api_key or config.settings.openai_api_key

        if not api_key:
            raise ValueError("未配置OpenAI API Key")

        self.client = OpenAI(api_key=api_key)

        log.info(f"OpenAI Agent初始化: {self.model}")

    def generate_cases(
            self,
            api_spec: Dict[str, Any],
            case_type: str,
            count: int = 10
    ) -> Dict[str, Any]:
        """
        生成测试用例

        Args:
            api_spec: API规格
            case_type: 用例类型（positive/negative/boundary/security）
            count: 生成数量

        Returns:
            生成的测试用例
        """
        # 加载提示词模板
        prompt_template = self.load_prompt_template(case_type)

        # 格式化提示词
        prompt = prompt_template.format(
            api_spec=self.format_api_spec(api_spec),
            count=count
        )

        log.info(f"使用OpenAI生成 {case_type} 用例（数量: {count}）")
        log.debug(f"Prompt长度: {len(prompt)} 字符")

        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的API测试工程师，精通各种测试场景设计。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 降低随机性
                max_tokens=4000
            )

            # 提取响应
            content = response.choices[0].message.content

            log.debug(f"OpenAI响应长度: {len(content)} 字符")

            # 解析JSON
            json_str = self.extract_json(content)
            result = json.loads(json_str)

            # 验证
            issues = self.validate_generated_cases(result)

            if issues:
                log.warning(f"生成的用例存在问题: {issues}")

            log.info(f"成功生成 {len(result.get('test_cases', []))} 个用例")

            return result

        except json.JSONDecodeError as e:
            log.error(f"JSON解析失败: {e}")
            log.error(f"原始响应: {content}")
            raise
        except Exception as e:
            log.error(f"OpenAI API调用失败: {e}")
            raise

    def generate_complete_suite(
            self,
            api_spec: Dict[str, Any],
            distribution: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """
        生成完整测试套件

        Args:
            api_spec: API规格
            distribution: 各类型用例分布
                默认: {"positive": 5, "negative": 10, "boundary": 8, "security": 5}

        Returns:
            完整的测试用例集合
        """
        if distribution is None:
            distribution = {
                "positive": 5,
                "negative": 10,
                "boundary": 8,
                "security": 5
            }

        all_cases = []

        for case_type, count in distribution.items():
            if count > 0:
                log.info(f"生成 {case_type} 用例: {count} 个")

                try:
                    result = self.generate_cases(api_spec, case_type, count)
                    all_cases.extend(result.get("test_cases", []))
                except Exception as e:
                    log.error(f"生成 {case_type} 用例失败: {e}")

        return {
            "metadata": {
                "description": "AI生成的完整测试套件",
                "total_cases": len(all_cases),
                "distribution": distribution,
                "generator": "OpenAI",
                "model": self.model
            },
            "test_cases": all_cases
        }

    def generate_raw(self, prompt: str) -> str:
        """生成原始响应"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的API测试专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            log.error(f"OpenAI请求失败: {e}")
            raise