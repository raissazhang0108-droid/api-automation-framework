"""
认证管理器
支持多种认证方式
"""
from typing import Dict, Optional
import requests
from config.settings import config
from utils.logger import log


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self.auth_config = config.auth
        self.settings = config.settings
        self._token: Optional[str] = None

    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        # Petstore API不需要认证，直接返回空
        # 如果配置了token，才使用
        if self.settings.api_token:
            return {"Authorization": f"Bearer {self.settings.api_token}"}

        # 否则返回空headers（适用于公开API）
        log.debug("使用无认证模式")
        return {}

auth_manager = AuthManager()