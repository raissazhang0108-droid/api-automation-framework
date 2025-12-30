"""
配置管理模块
支持多环境配置加载和验证
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings


class APIConfig(BaseModel):
    """API配置"""
    base_url: str
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 1


class AuthConfig(BaseModel):
    """认证配置"""
    type: str = "bearer"  # bearer, basic, api_key
    token_endpoint: str = "/auth/login"


class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str
    port: int = 5432
    name: str


class FeaturesConfig(BaseModel):
    """特性配置"""
    mock_enabled: bool = False
    debug_mode: bool = False
    strict_validation: bool = True


class ReportConfig(BaseModel):
    """上报配置"""
    enabled: bool = True
    url: str


class EnvironmentConfig(BaseModel):
    """环境配置"""
    api: APIConfig
    auth: AuthConfig
    database: DatabaseConfig
    features: FeaturesConfig
    report: ReportConfig


class Settings(BaseSettings):
    """
    全局设置

    Pydantic 2.x 配置说明：
    - 使用 model_config 替代 Config 类
    - extra='ignore' 允许额外字段但会忽略
    """

    # 从环境变量读取
    test_env: str = Field(default="dev", alias="TEST_ENV")
    api_username: Optional[str] = Field(default=None, alias="API_USERNAME")
    api_password: Optional[str] = Field(default=None, alias="API_PASSWORD")
    api_token: Optional[str] = Field(default=None, alias="API_TOKEN")

    # AI配置
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", alias="OPENAI_MODEL")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # 上报URL
    report_url: Optional[str] = Field(default=None, alias="REPORT_URL")

    # 日志级别
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Pydantic 2.x 配置
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 关键：忽略额外字段
    )


class ConfigManager:
    """配置管理器"""

    _instance = None
    _config: Dict[str, EnvironmentConfig] = {}
    _current_env: str = "dev"
    _settings: Optional[Settings] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化配置"""
        # 加载全局设置
        self._settings = Settings()

        # 加载环境配置文件
        config_file = Path(__file__).parent / "environments.yaml"

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # 解析环境配置
        for env_name, env_data in raw_config.items():
            self._config[env_name] = EnvironmentConfig(**env_data)

        # 设置当前环境
        self._current_env = self._settings.test_env

    def set_environment(self, env: str):
        """设置当前环境"""
        if env not in self._config:
            available = list(self._config.keys())
            raise ValueError(
                f"未知环境: {env}. 可用环境: {available}"
            )
        self._current_env = env

    def get_current_env(self) -> str:
        """获取当前环境名称"""
        return self._current_env

    def get_env_config(self) -> EnvironmentConfig:
        """获取当前环境配置"""
        return self._config[self._current_env]

    @property
    def settings(self) -> Settings:
        """获取全局设置"""
        return self._settings

    @property
    def api(self) -> APIConfig:
        """获取API配置"""
        return self.get_env_config().api

    @property
    def auth(self) -> AuthConfig:
        """获取认证配置"""
        return self.get_env_config().auth

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self.get_env_config().database

    @property
    def features(self) -> FeaturesConfig:
        """获取特性配置"""
        return self.get_env_config().features

    @property
    def report(self) -> ReportConfig:
        """获取上报配置"""
        return self.get_env_config().report

    @property
    def data_path(self) -> Path:
        """获取当前环境的数据目录"""
        base_path = Path(__file__).parent.parent / "test_data"
        return base_path / self._current_env


# 全局配置实例
config = ConfigManager()