from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # execution_id -> list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, execution_id: str, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = []
        self.active_connections[execution_id].append(websocket)

    def disconnect(self, execution_id: str, websocket: WebSocket):
        """断开连接"""
        if execution_id in self.active_connections:
            if websocket in self.active_connections[execution_id]:
                self.active_connections[execution_id].remove(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]

    async def send_message(self, execution_id: str, message: dict):
        """发送消息到指定执行的连接"""
        print(f"[WS] send_message to {execution_id}, connections={len(self.active_connections.get(execution_id, []))}")
        if execution_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[execution_id]:
                try:
                    print(f"[WS] Sending: {message}")
                    await connection.send_json(message)
                    print(f"[WS] Sent successfully")
                except Exception as e:
                    print(f"[WS] Send failed: {e}")
                    disconnected.append(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(execution_id, conn)

    async def send_node_update(
        self,
        execution_id: str,
        node_id: str,
        status: str,
        output: str = None
    ):
        """发送节点更新"""
        await self.send_message(execution_id, {
            "type": "node_update",
            "node_id": node_id,
            "status": status,
            "output": output
        })

    async def send_execution_update(
        self,
        execution_id: str,
        status: str,
        result_summary: dict = None
    ):
        """发送执行更新"""
        await self.send_message(execution_id, {
            "type": "execution_update",
            "status": status,
            "result_summary": result_summary
        })


# 全局实例
manager = ConnectionManager()
