"""Parameters for app config.
"""

import os

VOICE = "alloy"

LOG_EVENT_TYPES = [
    "response.content.done",
    "rate_limits.updated",
    "response.done",
    "input_audio_buffer.commited",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started",
    "session.created",
    "error",
]

API_AUTH_KEY = os.getenv("API_AUTH_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
