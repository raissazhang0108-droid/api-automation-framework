"""
RPC客户端（gRPC支持）
"""
from typing import Dict, Any, Optional
import grpc

from utils.logger import log


class RPCClient:
    """
    gRPC客户端封装

    注意：需要预先生成protobuf代码
    """

    def __init__(
            self,
            host: str,
            port: int,
            use_ssl: bool = False,
            timeout: int = 30
    ):
        """
        初始化RPC客户端

        Args:
            host: 服务器地址
            port: 端口
            use_ssl: 是否使用SSL
            timeout: 超时时间
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.channel = None

        self._connect()

    def _connect(self):
        """建立连接"""
        address = f"{self.host}:{self.port}"

        if self.use_ssl:
            credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.secure_channel(address, credentials)
        else:
            self.channel = grpc.insecure_channel(address)

        log.info(f"RPC客户端连接: {address}")

    def call(
            self,
            stub_class,
            method_name: str,
            request_message,
            metadata: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        调用RPC方法

        Args:
            stub_class: Stub类
            method_name: 方法名
            request_message: 请求消息
            metadata: 元数据（headers）

        Returns:
            响应消息
        """
        stub = stub_class(self.channel)
        method = getattr(stub, method_name)

        metadata_tuples = None
        if metadata:
            metadata_tuples = list(metadata.items())

        log.info(f"调用RPC方法: {method_name}")

        try:
            response = method(
                request_message,
                timeout=self.timeout,
                metadata=metadata_tuples
            )

            log.info("RPC调用成功")
            return response

        except grpc.RpcError as e:
            log.error(f"RPC调用失败: {e.code()} - {e.details()}")
            raise

    def close(self):
        """关闭连接"""
        if self.channel:
            self.channel.close()
            log.info("RPC连接已关闭")


# 使用示例
"""
# 1. 生成protobuf代码
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto

# 2. 使用
from generated import service_pb2, service_pb2_grpc

client = RPCClient("localhost", 50051)

request = service_pb2.UserRequest(user_id=123)
response = client.call(
    service_pb2_grpc.UserServiceStub,
    "GetUser",
    request
)

print(response)
client.close()
"""