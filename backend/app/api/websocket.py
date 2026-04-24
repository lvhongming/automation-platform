from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
import json

from app.db.database import async_session_maker
from app.services.websocket import manager
from app.core.security import verify_token

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/executions/{execution_id}")
async def execution_websocket(
    websocket: WebSocket,
    execution_id: str,
    token: str = Query(...)
):
    """执行状态 WebSocket"""
    # 验证 token
    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(execution_id, websocket)

    try:
        while True:
            # 保持连接，可以接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            # 处理客户端消息
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(execution_id, websocket)
    except Exception:
        manager.disconnect(execution_id, websocket)
