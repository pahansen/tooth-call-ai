import asyncio
import websockets
import json
import pyaudio
import audioop
import base64
import time

# Replace with your WebSocket endpoint
WEBSOCKET_ENDPOINT = "ws://localhost:8000/media-stream"

# Audio settings
MIC_RATE = 16000  # Initial recording rate (most microphones default to this)
TARGET_RATE = 24000  # Target rate for PCM
CHUNK = 1024  # Number of frames per buffer
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono audio


# Function to resample audio
def resample_audio(data, from_rate, to_rate):
    """Resample audio from one rate to another."""
    return audioop.ratecv(data, 2, CHANNELS, from_rate, to_rate, None)[0]


async def send_audio_to_websocket(websocket, stream):
    """Stream Base64-encoded raw PCM audio to the WebSocket server."""
    try:
        while True:
            # Capture audio chunk
            audio_chunk = stream.read(CHUNK, exception_on_overflow=False)

            # Resample to the target rate if necessary
            if MIC_RATE != TARGET_RATE:
                audio_chunk = resample_audio(
                    audio_chunk, MIC_RATE, TARGET_RATE)

            # Encode the audio chunk as Base64
            audio_payload = base64.b64encode(audio_chunk).decode("utf-8")

            current_timestamp = int(time.time() * 1000)
            # Prepare the media message
            media_message = {
                "event": "media",
                "media": {
                    "payload": audio_payload,  # Base64-encoded PCM data
                    "timestamp": current_timestamp
                }
            }
            # Send to the WebSocket server
            await websocket.send(json.dumps(media_message))
            # print(f"Sent audio chunk of size {len(audio_chunk)} bytes")
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"Error sending audio: {e}")


async def receive_and_play_audio(websocket, playback_stream):
    """Receive Base64-encoded audio from the WebSocket server and play it."""
    try:
        while True:
            # Receive message from the server
            message = await websocket.recv()
            response = json.loads(message)

            # Handle audio responses
            try:
                # Decode the Base64-encoded audio
                audio_chunk = base64.b64decode(response['media']['payload'])

                # Play the decoded audio
                playback_stream.write(audio_chunk)
                print(
                    f"Played received audio chunk of size {len(audio_chunk)} bytes")
            except Exception as e:
                print(f"Error decoding or playing audio: {e}")
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed by server.")
    except Exception as e:
        print(f"Error receiving audio: {e}")


async def main():
    """Main function to handle audio streaming and playback."""
    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Open microphone input stream
    mic_stream = audio.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=MIC_RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

    # Open playback stream
    playback_stream = audio.open(format=FORMAT,
                                 channels=CHANNELS,
                                 rate=TARGET_RATE,
                                 output=True)

    async with websockets.connect(WEBSOCKET_ENDPOINT) as websocket:
        print("Connected to the /media-stream endpoint")

        # Send start message
        start_message = {
            "event": "start",
            "start": {
                "streamSid": "exampleStream123"
            }
        }
        await websocket.send(json.dumps(start_message))
        print("Sent start message")

        # Run audio sending and receiving tasks concurrently
        await asyncio.gather(
            send_audio_to_websocket(websocket, mic_stream),
            receive_and_play_audio(websocket, playback_stream)
        )

    # Close audio streams
    mic_stream.stop_stream()
    mic_stream.close()
    playback_stream.stop_stream()
    playback_stream.close()
    audio.terminate()


if __name__ == "__main__":
    asyncio.run(main())
