import os
import json
import base64
import asyncio
import websockets

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from dotenv import load_dotenv
from app.tools.cal_tool import CalTool

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5050))

SYSTEM_MESSAGE = (
    """Du bist ein Assistent, der bei Kalenderbuchungen hilft. Du kannst Termine erstellen, stornieren und auch umbuchen.
    Das ist deine EINZIGE Aufgabe. Für alle anderen Anfragen antwortest du, dass du dabei nicht weiterhelfen kannst."""
)
VOICE = "alloy"

LOG_EVENT_TYPES = [
    "response.content.done", "rate_limits.updated", "response.done",
    "input_audio_buffer.commited", "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started", "session.created", "error"
]

app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API Key.")


@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Schedule it Voice Assistant is running!"}


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)
        stream_sid = None
        latest_media_timestamp = 0

        async def receive_from_client():
            """Receive audio data from client and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media':
                        latest_media_timestamp = int(
                            data['media']['timestamp'])
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                        latest_media_timestamp = 0

            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_client():
            nonlocal stream_sid
            try:
                async for open_message in openai_ws:
                    response = json.loads(open_message)
                    if response["type"] in LOG_EVENT_TYPES:
                        response_type = response["type"]
                        print(f"Received event: {response_type}", response)
                    if response["type"] == "session.updated":
                        print("Session updated succesfully:", response)

                    if response.get('type') == 'response.done':
                        for item in response['response']['output']:
                            if item['type'] == 'function_call' and item['status'] == 'completed':
                                try:
                                    await handle_function_call(item)
                                except Exception as e:
                                    print(
                                        f"Error processing function call: {e}")

                    if response.get('type') == 'response.audio.delta' and 'delta' in response:
                        try:
                            audio_payload = base64.b64encode(
                                base64.b64decode(response['delta'])).decode('utf-8')
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_payload
                                }
                            }
                            await websocket.send_json(audio_delta)

                        except Exception as e:
                            print(f"Error processing audio data: {e}")

            except Exception as e:
                print(f"Error sending audio to client: {e}")

        async def handle_function_call(function_call_item: dict):
            function_call_name = function_call_item["name"]
            function_call_arguments = json.loads(
                function_call_item['arguments'])
            function_call_result = None

            if function_call_name == "create_booking":
                function_call_result = CalTool.create_booking(function_call_arguments.get(
                    "start"), function_call_arguments.get("attendee_name"), function_call_arguments.get("additional_notes"))
            if function_call_name == "cancel_booking":
                function_call_result = CalTool.cancel_booking(function_call_arguments.get(
                    "uid"), function_call_arguments.get("start"), function_call_arguments.get("attendee_name"))

            if function_call_result:
                function_call_response = {
                    "type": "conversation.item.create",
                    "previous_item_id": function_call_item["id"],
                    "item": {
                        "id": function_call_item["id"] + "_fcr",
                        "type": "function_call_output",
                        "call_id": function_call_item["call_id"],
                        "output": function_call_result
                    }

                }
                await openai_ws.send(json.dumps(
                    function_call_response))

                user_feedback = {
                    "type": "response.create",
                    "response": {
                        "instructions": "Teile dem Nutzer das Ergebnis der Terminbuchung mit.",
                    }
                }

                await openai_ws.send(json.dumps(user_feedback))

        await asyncio.gather(receive_from_client(), send_to_client())


async def initialize_session(openai_ws):
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": [CalTool.get_create_booking_description(), CalTool.get_cancel_booking_description()]
        }
    }
    print("Sending session update:", json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))
