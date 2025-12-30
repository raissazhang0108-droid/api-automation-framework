"""
WebSocket客户端
"""
import asyncio
import json
from typing import Dict, Any, Optional, Callable
import websockets

from utils.logger import log


class WebSocketClient:
    """
    WebSocket客户端封装
    """

    def __init__(
            self,
            url: str,
            timeout: int = 30,
            ping_interval: int = 20,
            ping_timeout: int = 10
    ):
        """
        初始化WebSocket客户端

        Args:
            url: WebSocket URL (ws:// or wss://)
            timeout: 连接超时
            ping_interval: Ping间隔
            ping_timeout: Ping超时
        """
        self.url = url
        self.timeout = timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.websocket = None
        self.is_connected = False

    async def connect(self, headers: Optional[Dict[str, str]] = None):
        """建立连接"""
        log.info(f"连接WebSocket: {self.url}")

        try:
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=headers,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout
            )

            self.is_connected = True
            log.info("WebSocket连接成功")

        except Exception as e:
            log.error(f"WebSocket连接失败: {e}")
            raise

    async def send(self, message: Union[str, Dict]):
        """发送消息"""
        if not self.is_connected:
            raise RuntimeError("WebSocket未连接")

        if isinstance(message, dict):
            message = json.dumps(message)

        log.debug(f"发送消息: {message}")
        await self.websocket.send(message)

    async def receive(self, parse_json: bool = True) -> Union[str, Dict]:
        """接收消息"""
        if not self.is_connected:
            raise RuntimeError("WebSocket未连接")

        message = await self.websocket.recv()
        log.debug(f"接收消息: {message}")

        if parse_json:
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                return message

        return message

    async def listen(
            self,
            callback: Callable[[Union[str, Dict]], None],
            parse_json: bool = True
    ):
        """持续监听消息"""
        log.info("开始监听WebSocket消息")

        try:
            async for message in self.websocket:
                if parse_json:
                    try:
                        message = json.loads(message)
                    except json.JSONDecodeError:
                        pass

                callback(message)

        except websockets.exceptions.ConnectionClosed:
            log.warning("WebSocket连接已关闭")
            self.is_connected = False

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            log.info("WebSocket连接已关闭")


# 同步包装器（方便在pytest中使用）
class WebSocketClientSync:
    """WebSocket客户端（同步版本）"""

    def __init__(self, url: str, **kwargs):
        self.async_client = WebSocketClient(url, **kwargs)
        self.loop = asyncio.new_event_loop()

    def connect(self, headers: Optional[Dict[str, str]] = None):
        """连接"""
        self.loop.run_until_complete(self.async_client.connect(headers))

    def send(self, message):
        """发送"""
        self.loop.run_until_complete(self.async_client.send(message))

    def receive(self, parse_json: bool = True):
        """接收"""
        return self.loop.run_until_complete(
            self.async_client.receive(parse_json)
        )

    def close(self):
        """关闭"""
        self.loop.run_until_complete(self.async_client.close())
        self.loop.close()


# 使用示例
"""
# 异步使用
async def test_websocket():
    client = WebSocketClient("ws://localhost:8000/ws")
    await client.connect()

    await client.send({"type": "subscribe", "channel": "updates"})

    message = await client.receive()
    print(message)

    await client.close()

asyncio.run(test_websocket())

# 同步使用（在pytest中）
def test_websocket_sync():
    client = WebSocketClientSync("ws://localhost:8000/ws")
    client.connect()

    client.send({"type": "ping"})
    response = client.receive()

    assert response["type"] == "pong"

    client.close()
"""