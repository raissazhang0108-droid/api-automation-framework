"""
文件上传工具
支持多文件上传、进度跟踪
"""
from typing import Dict, List, Union, Optional
from pathlib import Path
import mimetypes

from core.http_client import HTTPClient
from utils.logger import log


class FileUploader:
    """文件上传器"""

    def __init__(self, client: HTTPClient):
        self.client = client

    def upload_single(
            self,
            endpoint: str,
            file_path: Union[str, Path],
            field_name: str = "file",
            metadata: Optional[Dict] = None
    ) -> dict:
        """
        上传单个文件

        Args:
            endpoint: 上传端点
            file_path: 文件路径
            field_name: 表单字段名
            metadata: 元数据

        Returns:
            响应JSON
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        log.info(f"上传文件: {file_path.name}")

        with open(file_path, "rb") as f:
            files = {
                field_name: (
                    file_path.name,
                    f,
                    self._get_mime_type(file_path)
                )
            }

            response = self.client.post(
                endpoint,
                files=files,
                data=metadata
            )

            response.raise_for_status()
            return response.json()

    def upload_multiple(
            self,
            endpoint: str,
            file_paths: List[Union[str, Path]],
            field_name: str = "files",
            metadata: Optional[Dict] = None
    ) -> dict:
        """
        上传多个文件

        Args:
            endpoint: 上传端点
            file_paths: 文件路径列表
            field_name: 表单字段名
            metadata: 元数据

        Returns:
            响应JSON
        """
        files = []

        for file_path in file_paths:
            file_path = Path(file_path)

            if not file_path.exists():
                log.warning(f"文件不存在，跳过: {file_path}")
                continue

            files.append(
                (field_name, (
                    file_path.name,
                    open(file_path, "rb"),
                    self._get_mime_type(file_path)
                ))
            )

        if not files:
            raise ValueError("没有有效的文件可上传")

        log.info(f"批量上传 {len(files)} 个文件")

        try:
            response = self.client.post(
                endpoint,
                files=files,
                data=metadata
            )

            response.raise_for_status()
            return response.json()

        finally:
            # 关闭文件句柄
            for _, (_, f, _) in files:
                f.close()

    def upload_base64(
            self,
            endpoint: str,
            file_path: Union[str, Path],
            metadata: Optional[Dict] = None
    ) -> dict:
        """
        以Base64编码上传文件

        Args:
            endpoint: 上传端点
            file_path: 文件路径
            metadata: 元数据

        Returns:
            响应JSON
        """
        import base64

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        payload = {
            "filename": file_path.name,
            "content": encoded,
            "mime_type": self._get_mime_type(file_path)
        }

        if metadata:
            payload.update(metadata)

        log.info(f"以Base64上传: {file_path.name}")

        response = self.client.post(endpoint, json=payload)
        response.raise_for_status()

        return response.json()

    def _get_mime_type(self, file_path: Path) -> str:
        """获取MIME类型"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"


# 使用示例
if __name__ == "__main__":
    from core.http_client import create_client

    client = create_client()
    uploader = FileUploader(client)

    # 单文件上传
    result = uploader.upload_single(
        "/api/v1/upload",
        "test.jpg",
        metadata={"description": "Test image"}
    )
    print(result)