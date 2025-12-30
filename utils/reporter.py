"""
测试数据上报工具
"""
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
from config.settings import config
from utils.logger import log


class TestReporter:
    """测试结果上报器"""

    def __init__(self):
        self.report_config = config.report
        self.session = requests.Session()

    def report_test_execution(
            self,
            test_name: str,
            url_path: str,
            method: str,
            status: str,
            duration: float,
            status_code: Optional[int] = None,
            error_message: Optional[str] = None
    ) -> bool:
        """
        上报测试执行结果

        Args:
            test_name: 测试用例名称
            url_path: API路径
            method: HTTP方法
            status: 测试状态 (passed/failed/skipped)
            duration: 执行时长（秒）
            status_code: HTTP状态码
            error_message: 错误信息

        Returns:
            是否上报成功
        """
        if not self.report_config.enabled:
            log.debug("测试上报未启用")
            return True

        payload = {
            "test_name": test_name,
            "url_path": url_path,
            "method": method.upper(),
            "status": status,
            "duration": duration,
            "status_code": status_code,
            "error_message": error_message,
            "environment": config.get_current_env(),
            "timestamp": datetime.now().isoformat()
        }

        try:
            response = self.session.post(
                self.report_config.url,
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                log.debug(f"上报成功: {test_name}")
                return True
            else:
                log.warning(f"上报失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            log.error(f"上报异常: {e}")
            return False

    def batch_report(self, results: list) -> bool:
        """批量上报"""
        if not self.report_config.enabled:
            return True

        try:
            response = self.session.post(
                f"{self.report_config.url}/batch",
                json={"results": results},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            log.error(f"批量上报失败: {e}")
            return False


# 全局上报器
reporter = TestReporter()