# Tooth Call AI
An example project using OpenAI realtime API for an AI assistant built to support dental practice teams by managing phone reception tasks. 
It can answer patient calls, schedule appointments, and provide essential information, helping streamline workflows and improve patient satisfaction.

## Dependencies
The voice assistant is based on the OpenAI realtime API https://platform.openai.com/docs/guides/realtime?text-generation-quickstart-example=audio. As a main tool, the AI uses some implemented features of the calendar API from https://cal.com/de. For both platforms, an API key is required that should be set as `OPENAI_API_KEY` and `CAL_API_KEY`.

## How to run
FastAPI is used as a framework to run the API / websocket endpoints. You can run the app with uvicorn: ```uvicorn app.main:app```.
Once the app is up and running, you can connect to the voice assistant using the local test client in `/test_client/local_test_client.py`. This test client will take the input from your default microphone and stream it to the opened websocket connection. Once the OpenAI realtime API detects a pause, it will feed back the sound output of the OpenAI realtime API to your default speaker.

