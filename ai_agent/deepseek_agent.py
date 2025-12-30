"""
DeepSeek Agent实现
"""
from typing import Dict, Any
import json
import requests

from ai_agent.base_agent import BaseAgent
from config.settings import config
from utils.logger import log


class DeepSeekAgent(BaseAgent):
    """
    DeepSeek Agent
    使用DeepSeek API生成测试用例
    """

    def __init__(self, model: str = "deepseek-chat", api_key: str = None):
        """
        初始化DeepSeek Agent

        Args:
            model: 模型名称
            api_key: API密钥
        """
        super().__init__(model)

        self.api_key = api_key or config.settings.deepseek_api_key

        if not self.api_key:
            raise ValueError("未配置DeepSeek API Key")

        self.api_url = "https://api.deepseek.com/v1/chat/completions"

        log.info(f"DeepSeek Agent初始化: {self.model}")

    def generate_cases(
            self,
            api_spec: Dict[str, Any],
            case_type: str,
            count: int = 10
    ) -> Dict[str, Any]:
        """生成测试用例"""

        # 加载提示词模板
        prompt_template = self.load_prompt_template(case_type)

        # 格式化提示词
        prompt = prompt_template.format(
            api_spec=self.format_api_spec(api_spec),
            count=count
        )

        log.info(f"使用DeepSeek生成 {case_type} 用例（数量: {count}）")

        try:
            # 调用DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的API测试工程师，精通各种测试场景设计。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            response.raise_for_status()

            # 解析响应
            result_data = response.json()
            content = result_data["choices"][0]["message"]["content"]

            log.debug(f"DeepSeek响应长度: {len(content)} 字符")

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
            log.error(f"DeepSeek API调用失败: {e}")
            raise

    def generate_complete_suite(
            self,
            api_spec: Dict[str, Any],
            distribution: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """生成完整测试套件"""
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
                "generator": "DeepSeek",
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
            log.error(f"DeepSeek请求失败: {e}")
            raise