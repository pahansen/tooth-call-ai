import base64
import json

from fastapi.websockets import WebSocketDisconnect

from app.config import LOG_EVENT_TYPES, VOICE
from app.prompts.prompt_file_paths import INTRO_SPEECH, SYSTEM
from app.tools.cal_tool import CalTool
from app.tools.notify_staff_tool import NotifyStaffTool


async def initialize_session(openai_ws):
    with open(SYSTEM) as file:
        system_prompt = file.read()
    with open(INTRO_SPEECH) as file:
        intro_speech_prompt = file.read()

    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "voice": VOICE,
            "instructions": system_prompt,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": [
                CalTool.get_create_booking_description(),
                CalTool.get_cancel_booking_description(),
                NotifyStaffTool.get_create_call_back_description()
            ],
        },
    }
    intro_speech = {
        "type": "response.create",
        "response": {
            "instructions": intro_speech_prompt,
        },
    }

    print("Sending session update:", json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))
    await openai_ws.send(json.dumps(intro_speech))


async def receive_from_client(stream_sid, latest_media_timestamp, websocket, openai_ws):
    """Receive audio data from client and send it to the OpenAI Realtime API."""
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            if data["event"] == "media":
                latest_media_timestamp = int(data["media"]["timestamp"])
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": data["media"]["payload"],
                }
                await openai_ws.send(json.dumps(audio_append))
            elif data["event"] == "start":
                stream_sid = data["start"]["streamSid"]
                print(f"Incoming stream has started {stream_sid}")
                latest_media_timestamp = 0

    except WebSocketDisconnect:
        print("Client disconnected.")
        if openai_ws.open:
            await openai_ws.close()


async def send_to_client(stream_sid, websocket, openai_ws):
    try:
        async for open_message in openai_ws:
            response = json.loads(open_message)
            if response["type"] in LOG_EVENT_TYPES:
                response_type = response["type"]
                print(f"Received event: {response_type}", response)
            if response["type"] == "session.updated":
                print("Session updated succesfully:", response)

            if response.get("type") == "response.done":
                for item in response["response"]["output"]:
                    if (
                        item["type"] == "function_call"
                        and item["status"] == "completed"
                    ):
                        try:
                            await handle_function_call(openai_ws, item)
                        except Exception as e:
                            print(f"Error processing function call: {e}")

            if response.get("type") == "response.audio.delta" and "delta" in response:
                try:
                    audio_payload = base64.b64encode(
                        base64.b64decode(response["delta"])
                    ).decode("utf-8")
                    audio_delta = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": audio_payload},
                    }
                    await websocket.send_json(audio_delta)

                except Exception as e:
                    print(f"Error processing audio data: {e}")

    except Exception as e:
        print(f"Error sending audio to client: {e}")


async def handle_function_call(openai_ws, function_call_item: dict):
    function_call_name = function_call_item["name"]
    function_call_arguments = json.loads(function_call_item["arguments"])
    function_call_result = None

    if function_call_name == "create_booking":
        function_call_result = CalTool.create_booking(
            function_call_arguments.get("start"),
            function_call_arguments.get("attendee_name"),
            function_call_arguments.get("additional_notes"),
        )
    if function_call_name == "cancel_booking":
        function_call_result = CalTool.cancel_booking(
            function_call_arguments.get("uid"),
            function_call_arguments.get("start"),
            function_call_arguments.get("attendee_name"),
        )

    if function_call_result:
        function_call_response = {
            "type": "conversation.item.create",
            "previous_item_id": function_call_item["id"],
            "item": {
                "id": function_call_item["id"] + "_fcr",
                "type": "function_call_output",
                "call_id": function_call_item["call_id"],
                "output": function_call_result,
            },
        }
        await openai_ws.send(json.dumps(function_call_response))

        user_feedback = {
            "type": "response.create",
            "response": {
                "instructions": "Teile dem Nutzer das Ergebnis der Terminbuchung mit.",
            },
        }

        await openai_ws.send(json.dumps(user_feedback))
