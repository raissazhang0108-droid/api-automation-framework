"""
Ollama Agent实现（本地AI）
"""
from typing import Dict, Any
import json
import requests

from ai_agent.base_agent import BaseAgent
from config.settings import config
from utils.logger import log


class OllamaAgent(BaseAgent):
    """
    Ollama Agent
    使用本地Ollama模型生成测试用例
    """

    def __init__(self, model: str = None, base_url: str = None):
        """
        初始化Ollama Agent

        Args:
            model: 模型名称（如 llama3.2, deepseek-r1:8b）
            base_url: Ollama服务地址
        """
        model = model or config.settings.ollama_model
        super().__init__(model)

        self.base_url = base_url or config.settings.ollama_base_url
        self.api_url = f"{self.base_url}/api/generate"

        log.info(f"Ollama Agent初始化: {self.model} @ {self.base_url}")

        # 检查连接
        self._check_connection()

    def _check_connection(self):
        """检查Ollama服务连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            log.info("Ollama服务连接成功")
        except Exception as e:
            log.error(f"Ollama服务连接失败: {e}")
            log.error(f"请确保Ollama服务已启动: ollama serve")
            raise

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
            case_type: 用例类型
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

        log.info(f"使用Ollama生成 {case_type} 用例（数量: {count}）")

        try:
            # 调用Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 4000
                }
            }

            log.debug("调用Ollama API...")

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120  # Ollama可能较慢
            )

            response.raise_for_status()

            # 解析响应
            result_data = response.json()
            content = result_data.get("response", "")

            log.debug(f"Ollama响应长度: {len(content)} 字符")

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
            log.error(f"原始响应: {content[:500]}...")
            raise
        except requests.exceptions.Timeout:
            log.error("Ollama请求超时，模型可能较大或服务器负载过高")
            raise
        except Exception as e:
            log.error(f"Ollama API调用失败: {e}")
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
                "generator": "Ollama",
                "model": self.model
            },
            "test_cases": all_cases
        }

    def generate_raw(self, prompt: str) -> str:
        """生成原始响应"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2000
            }
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            log.error(f"Ollama请求失败: {e}")
            raise