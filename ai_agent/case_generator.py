"""
测试用例生成器（统一接口）
"""
from typing import Dict, Any, Optional
from enum import Enum

from ai_agent.openai_agent import OpenAIAgent
from ai_agent.ollama_agent import OllamaAgent
from ai_agent.deepseek_agent import DeepSeekAgent
from utils.logger import log


class AIProvider(str, Enum):
    """AI提供商"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


class CaseGenerator:
    """
    测试用例生成器
    统一的AI生成接口
    """

    def __init__(
            self,
            provider: AIProvider = AIProvider.OPENAI,
            model: Optional[str] = None,
            api_key: Optional[str] = None
    ):
        """
        初始化生成器

        Args:
            provider: AI提供商
            model: 模型名称
            api_key: API密钥（Ollama不需要）
        """
        self.provider = provider

        # 创建对应的Agent
        if provider == AIProvider.OPENAI:
            self.agent = OpenAIAgent(model=model, api_key=api_key)
        elif provider == AIProvider.OLLAMA:
            self.agent = OllamaAgent(model=model)
        elif provider == AIProvider.DEEPSEEK:
            self.agent = DeepSeekAgent(model=model, api_key=api_key)
        else:
            raise ValueError(f"不支持的AI提供商: {provider}")

        log.info(f"测试用例生成器初始化: {provider.value}")

    def generate(
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
        return self.agent.generate_cases(api_spec, case_type, count)

    def generate_suite(
            self,
            api_spec: Dict[str, Any],
            distribution: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        生成完整测试套件

        Args:
            api_spec: API规格
            distribution: 各类型用例分布

        Returns:
            完整的测试用例集合
        """
        return self.agent.generate_complete_suite(api_spec, distribution)


# 便捷函数
def create_generator(
        provider: str = "openai",
        **kwargs
) -> CaseGenerator:
    """
    创建生成器

    Args:
        provider: 提供商名称（openai/ollama/deepseek）
        **kwargs: 其他参数

    Returns:
        CaseGenerator实例
    """
    provider_enum = AIProvider(provider.lower())
    return CaseGenerator(provider=provider_enum, **kwargs)