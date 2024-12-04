import asyncio

import websockets
from fastapi import APIRouter, Header, HTTPException, WebSocket

from app.api.media_stream.services import (
    initialize_session,
    receive_from_client,
    send_to_client,
)
from app.config import API_AUTH_KEY, OPENAI_API_KEY

router = APIRouter()


@router.websocket("/media-stream")
async def handle_media_stream(
    websocket: WebSocket, authorization: str = Header(alias="Authorization")
):
    # Check for Authorization header
    if authorization != f"Bearer {API_AUTH_KEY}":
        await websocket.close(code=1008)  # Policy Violation
        raise HTTPException(status_code=401, detail="Unauthorized")

    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        },
    ) as openai_ws:
        await initialize_session(openai_ws)
        stream_sid = None
        latest_media_timestamp = 0

        await asyncio.gather(
            receive_from_client(
                stream_sid, latest_media_timestamp, websocket, openai_ws
            ),
            send_to_client(stream_sid, websocket, openai_ws),
        )
