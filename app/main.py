"""FastAPI setup.
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.media_stream.routes import router as media_stream_router

load_dotenv()

app = FastAPI()
app.include_router(media_stream_router)


@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Tooth call AI Voice Assistant is running!"}
