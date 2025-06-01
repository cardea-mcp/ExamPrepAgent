# app.py - Add these imports and endpoint
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database.monogodb import MongoDB
from llm_api import initialize_mcp_server, process_message, cleanup_server, process_audio_message
from audio_processing.whisper_handler import whisper_handler
from audio_processing.audio_utils import validate_audio_file, MAX_FILE_SIZE
import atexit
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ExamBOT API")

mongo_db = MongoDB()
available_functions = initialize_mcp_server()

atexit.register(cleanup_server)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Existing Pydantic models...
class UserCreate(BaseModel):
    name: str

class MessageSend(BaseModel):
    message: str

class SessionCreate(BaseModel):
    name: Optional[str] = None

class SessionUpdate(BaseModel):
    name: str

# Existing API Routes...
@app.post("/api/users")
async def create_user(user: UserCreate):
    """Create or get a user"""
    user_id = mongo_db.create_user(user.name)
    return {"user_id": user_id, "name": user.name}

@app.get("/api/users/{user_name}")
async def get_user(user_name: str):
    """Get user by name"""
    user = mongo_db.get_user_by_name(user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users/{user_id}/sessions")
async def create_session(user_id: str, session: SessionCreate):
    """Create a new chat session"""
    session_id = mongo_db.create_session(user_id, session.name)
    return {"session_id": session_id}

@app.get("/api/users/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    sessions = mongo_db.get_user_sessions(user_id)
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def get_session_context(session_id: str):
    """Get session context/chat history"""
    context = mongo_db.get_session_context(session_id)
    return {"context": context}

@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, message: MessageSend):
    """Send a message to the chatbot"""
    try:
        response = await process_message(session_id, message.message, available_functions)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Audio upload endpoint
@app.post("/api/sessions/{session_id}/audio")
async def send_audio_message(
    session_id: str,
    audio_file: UploadFile = File(...),
    language: Optional[str] = None
):
    """Send an audio message to the chatbot"""
    try:
        # Validate file size
        contents = await audio_file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Validate audio file
        is_valid, error_message = validate_audio_file(
            contents, 
            audio_file.filename or "audio.wav",
            audio_file.content_type
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Process audio and get response
        response = await process_audio_message(
            session_id, 
            contents, 
            audio_file.filename or "audio.wav",
            available_functions,
            language
        )
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Audio processing failed")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = mongo_db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """Update session name"""
    success = mongo_db.update_session_name(session_id, update.name)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated successfully"}

# NEW: Audio capability check endpoint
@app.get("/api/audio/support")
async def check_audio_support():
    """Check if audio processing is available"""
    try:
        # Try to load Whisper model
        model_loaded = whisper_handler.load_model()
        
        return {
            "supported": model_loaded,
            "model_size": whisper_handler.model_size,
            "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
            "supported_formats": whisper_handler.get_supported_formats()
        }
    except Exception as e:
        logger.error(f"Audio support check failed: {str(e)}")
        return {
            "supported": False,
            "error": str(e)
        }

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)