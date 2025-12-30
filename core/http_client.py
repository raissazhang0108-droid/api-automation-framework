"""
HTTP客户端封装
支持认证、重试、超时、文件上传等
"""
import time
import requests
from typing import Dict, Any, Optional, Union
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import config
from core.auth_manager import auth_manager
from utils.logger import log
from utils.reporter import reporter


class HTTPClient:
    """
    HTTP客户端

    特性：
    - 自动认证
    - 自动重试
    - 请求/响应日志
    - 数据上报
    - 文件上传
    - 超时控制
    """

    def __init__(
            self,
            base_url: Optional[str] = None,
            timeout: Optional[int] = None,
            retry_count: Optional[int] = None,
            verify_ssl: bool = False
    ):
        """
        初始化HTTP客户端

        Args:
            base_url: 基础URL（默认从配置读取）
            timeout: 超时时间（秒）
            retry_count: 重试次数
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url or config.api.base_url
        self.timeout = timeout or config.api.timeout
        self.retry_count = retry_count or config.api.retry_count
        self.verify_ssl = verify_ssl

        # 创建session
        self.session = self._create_session()

        # 默认headers
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "API-Automation-Framework/1.0"
        }

        # 添加认证headers
        auth_headers = auth_manager.get_auth_headers()
        self.default_headers.update(auth_headers)

        log.info(f"HTTP客户端初始化: {self.base_url}")

    def _create_session(self) -> requests.Session:
        """创建带重试机制的Session"""
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=config.api.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint

        # 确保base_url和endpoint之间有且只有一个斜杠
        base = self.base_url.rstrip("/")
        path = endpoint.lstrip("/")
        return f"{base}/{path}"

    def _merge_headers(
            self,
            headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """合并headers"""
        merged = self.default_headers.copy()
        if headers:
            merged.update(headers)
        return merged

    def _log_request(
            self,
            method: str,
            url: str,
            headers: Dict[str, str],
            **kwargs
    ):
        """记录请求日志"""
        log.debug("=" * 80)
        log.debug(f"📤 {method} {url}")
        log.debug(f"Headers: {self._safe_log_headers(headers)}")

        if "params" in kwargs and kwargs["params"]:
            log.debug(f"Params: {kwargs['params']}")

        if "json" in kwargs and kwargs["json"]:
            log.debug(f"Body: {kwargs['json']}")

        if "data" in kwargs and kwargs["data"]:
            log.debug(f"Data: {kwargs['data']}")

    def _log_response(self, response: requests.Response, duration: float):
        """记录响应日志"""
        log.debug(f"📥 Status: {response.status_code}")
        log.debug(f"⏱️  Duration: {duration:.3f}s")

        # 记录响应头（部分）
        important_headers = ["Content-Type", "Content-Length", "Date"]
        for header in important_headers:
            if header in response.headers:
                log.debug(f"{header}: {response.headers[header]}")

        # 记录响应体（限制长度）
        try:
            response_text = response.text
            if len(response_text) > 1000:
                log.debug(f"Response (truncated): {response_text[:1000]}...")
            else:
                log.debug(f"Response: {response_text}")
        except:
            log.debug("Response body could not be decoded")

        log.debug("=" * 80)

    def _safe_log_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """安全记录headers（隐藏敏感信息）"""
        safe_headers = headers.copy()
        sensitive_keys = ["Authorization", "X-API-Key", "Cookie", "Token"]

        for key in sensitive_keys:
            if key in safe_headers:
                value = safe_headers[key]
                if len(value) > 10:
                    safe_headers[key] = f"{value[:10]}...***"
                else:
                    safe_headers[key] = "***"

        return safe_headers

    def _report_execution(
            self,
            test_name: str,
            method: str,
            endpoint: str,
            response: requests.Response,
            duration: float,
            error: Optional[Exception] = None
    ):
        """上报测试执行结果"""
        if error:
            status = "failed"
            status_code = None
            error_message = str(error)
        else:
            status = "passed" if 200 <= response.status_code < 300 else "failed"
            status_code = response.status_code
            error_message = None

        reporter.report_test_execution(
            test_name=test_name,
            url_path=endpoint,
            method=method,
            status=status,
            duration=duration,
            status_code=status_code,
            error_message=error_message
        )

    def request(
            self,
            method: str,
            endpoint: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            files: Optional[Dict[str, Any]] = None,
            timeout: Optional[int] = None,
            allow_redirects: bool = True,
            verify: Optional[bool] = None,
            test_name: Optional[str] = None,
            **kwargs
    ) -> requests.Response:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            headers: 请求头
            params: URL参数
            json: JSON数据
            data: 表单数据
            files: 文件上传
            timeout: 超时时间
            allow_redirects: 是否允许重定向
            verify: 是否验证SSL
            test_name: 测试名称（用于上报）
            **kwargs: 其他requests参数

        Returns:
            Response对象
        """
        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)
        timeout = timeout or self.timeout
        verify = verify if verify is not None else self.verify_ssl

        # 如果上传文件，移除Content-Type让requests自动设置
        if files:
            merged_headers.pop("Content-Type", None)

        # 记录请求
        self._log_request(
            method=method,
            url=url,
            headers=merged_headers,
            params=params,
            json=json,
            data=data,
            files=files
        )

        # 发送请求
        start_time = time.time()
        error = None

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=merged_headers,
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=timeout,
                allow_redirects=allow_redirects,
                verify=verify,
                **kwargs
            )

            duration = time.time() - start_time

            # 记录响应
            self._log_response(response, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            error = e
            log.error(f"❌ 请求失败: {e}")
            raise

        finally:
            # 上报
            if test_name:
                self._report_execution(
                    test_name=test_name,
                    method=method,
                    endpoint=endpoint,
                    response=response if not error else None,
                    duration=duration,
                    error=error
                )

    def get(
            self,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> requests.Response:
        """GET请求"""
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
            self,
            endpoint: str,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            **kwargs
    ) -> requests.Response:
        """POST请求"""
        return self.request("POST", endpoint, json=json, data=data, **kwargs)

    def put(
            self,
            endpoint: str,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            **kwargs
    ) -> requests.Response:
        """PUT请求"""
        return self.request("PUT", endpoint, json=json, data=data, **kwargs)

    def delete(
            self,
            endpoint: str,
            **kwargs
    ) -> requests.Response:
        """DELETE请求"""
        return self.request("DELETE", endpoint, **kwargs)

    def patch(
            self,
            endpoint: str,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            **kwargs
    ) -> requests.Response:
        """PATCH请求"""
        return self.request("PATCH", endpoint, json=json, data=data, **kwargs)

    def upload_file(
            self,
            endpoint: str,
            file_path: Union[str, Path],
            field_name: str = "file",
            additional_data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> requests.Response:
        """
        上传文件

        Args:
            endpoint: API端点
            file_path: 文件路径
            field_name: 表单字段名
            additional_data: 额外的表单数据
            **kwargs: 其他请求参数

        Returns:
            Response对象
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        log.info(f"上传文件: {file_path.name} ({file_path.stat().st_size} bytes)")

        with open(file_path, "rb") as f:
            files = {field_name: (file_path.name, f, self._guess_mime_type(file_path))}

            return self.request(
                "POST",
                endpoint,
                files=files,
                data=additional_data,
                **kwargs
            )

    def _guess_mime_type(self, file_path: Path) -> str:
        """猜测MIME类型"""
        import mimetypes

        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    def download_file(
            self,
            endpoint: str,
            save_path: Union[str, Path],
            **kwargs
    ) -> Path:
        """
        下载文件

        Args:
            endpoint: API端点
            save_path: 保存路径
            **kwargs: 其他请求参数

        Returns:
            保存的文件路径
        """
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        log.info(f"下载文件到: {save_path}")

        response = self.get(endpoint, stream=True, **kwargs)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        log.info(f"下载完成: {save_path.stat().st_size} bytes")

        return save_path

    def set_auth_token(self, token: str):
        """设置认证Token"""
        self.default_headers["Authorization"] = f"Bearer {token}"
        log.info("认证Token已更新")

    def clear_auth_token(self):
        """清除认证Token"""
        self.default_headers.pop("Authorization", None)
        log.info("认证Token已清除")

    def close(self):
        """关闭Session"""
        self.session.close()
        log.info("HTTP客户端已关闭")


# 便捷函数
def create_client(
        base_url: Optional[str] = None,
        **kwargs
) -> HTTPClient:
    """创建HTTP客户端"""
    return HTTPClient(base_url=base_url, **kwargs)