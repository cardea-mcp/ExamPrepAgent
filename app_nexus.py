from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database.monogodb import MongoDB
from llm_api_nexus import process_message, process_audio_message  # Updated import
from audio_processing.whisper_handler import whisper_handler 
from audio_processing.audio_utils import validate_audio_file, MAX_FILE_SIZE, get_file_extension, cleanup_temp_file
from audio_processing.tts_handler import tts_handler
import atexit
import logging
import tempfile 
import ffmpeg
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ExamBOT API - Llama-Nexus Edition")

mongo_db = MongoDB()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models (unchanged)
class UserCreate(BaseModel):
    name: str

class MessageSend(BaseModel):
    message: str

class SessionCreate(BaseModel):
    name: Optional[str] = None

class SessionUpdate(BaseModel):
    name: str

# Audio transcoding function (unchanged)
def transcode_to_wav(input_file_path: str, output_file_path: str) -> bool:
    try:
        logger.info(f"Transcoding '{input_file_path}' to WAV at '{output_file_path}'")
        (
            ffmpeg
            .input(input_file_path)
            .output(output_file_path, format='wav', acodec='pcm_s16le', ar='16000', ac=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"Transcoding successful: '{output_file_path}'")
        return True
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg transcoding error: {e.stderr.decode('utf8')}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during transcoding: {str(e)}")
        return False

# API Routes (unchanged user/session management)
@app.post("/api/users")
async def create_user(user: UserCreate):
    user_id = mongo_db.create_user(user.name)
    return {"user_id": user_id, "name": user.name}

@app.get("/api/users/{user_name}")
async def get_user(user_name: str):
    user = mongo_db.get_user_by_name(user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users/{user_id}/sessions")
async def create_session(user_id: str, session: SessionCreate):
    session_id = mongo_db.create_session(user_id, session.name)
    return {"session_id": session_id}

@app.get("/api/users/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    sessions = mongo_db.get_user_sessions(user_id)
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def get_session_context(session_id: str):
    context = mongo_db.get_session_context(session_id)
    return {"context": context}

# Updated message endpoint (no longer needs available_functions)
@app.post("/api/sessions/{session_id}/messages")
async def send_message_route(session_id: str, message: MessageSend): 
    try:
        response = await process_message(session_id, message.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Message processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Updated audio endpoint
@app.post("/api/sessions/{session_id}/audio")
async def send_audio_message_route( 
    session_id: str,
    audio_file: UploadFile = File(...),
    language: Optional[str] = None
):
    temp_input_file_path = None
    temp_wav_file_path = None

    try:
        # Audio processing (unchanged)
        contents = await audio_file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        original_filename = audio_file.filename or "audio_upload"
        is_valid, error_message = validate_audio_file(
            contents,
            original_filename,
            audio_file.content_type
        )
        
        if not is_valid:
            logger.warning(f"Audio validation failed: {error_message}. Attempting transcoding anyway.")

        # Save and transcode audio
        original_ext = get_file_extension(original_filename)
        if not original_ext:
            original_ext = ".webm"
            original_filename += original_ext

        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_in:
            tmp_in.write(contents)
            temp_input_file_path = tmp_in.name
        
        logger.info(f"Audio file saved to temp: '{temp_input_file_path}'")

        temp_wav_file_path = tempfile.mktemp(suffix=".wav")

        transcode_success = transcode_to_wav(temp_input_file_path, temp_wav_file_path)
        if not transcode_success:
            raise HTTPException(status_code=500, detail="Audio transcoding failed.")

        with open(temp_wav_file_path, 'rb') as f_wav:
            wav_contents = f_wav.read()

        # Process through llama-nexus (no available_functions needed)
        response = await process_audio_message(
            session_id,
            wav_contents,
            os.path.basename(temp_wav_file_path),
            None,  # No available_functions needed
            language
        )
        
        # Add TTS if enabled
        if response.get("success") and response.get("response"):
            detected_lang = response.get("detected_language", "en")
            tts_lang = detected_lang if tts_handler.is_language_supported(detected_lang) else "en"
            
            tts_result = tts_handler.text_to_speech(response["response"], language=tts_lang)
            
            if tts_result["success"]:
                response["tts_audio"] = tts_result["audio_data"]
                response["tts_format"] = tts_result["format"]
            else:
                logger.warning(f"TTS generation failed: {tts_result['error']}")
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    finally:
        if temp_input_file_path:
            cleanup_temp_file(temp_input_file_path)
        if temp_wav_file_path:
            cleanup_temp_file(temp_wav_file_path)

# Remaining endpoints (unchanged)
@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    success = mongo_db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    success = mongo_db.update_session_name(session_id, update.name)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated successfully"}

@app.get("/api/audio/support")
async def check_audio_support():
    try:
        api_key_is_set = whisper_handler.is_model_loaded()
        return {
            "supported": api_key_is_set,
            "model_info": "Transcription via llama-nexus",
            "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
            "supported_formats": whisper_handler.get_supported_formats() 
        }
    except Exception as e:
        logger.error(f"Audio support check failed: {str(e)}")
        return {"supported": False, "error": str(e)}

@app.post("/api/tts")
async def text_to_speech_endpoint(request: dict):
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        slow = request.get("slow", False)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = tts_handler.text_to_speech(text, language, slow)
        
        if result["success"]:
            return {
                "success": True,
                "audio_data": result["audio_data"],
                "format": result["format"],
                "language": result["language"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"TTS endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tts/support")
async def check_tts_support():
    try:
        return {
            "supported": True,
            "languages": tts_handler.get_supported_languages(),
            "default_language": tts_handler.default_language
        }
    except Exception as e:
        logger.error(f"TTS support check failed: {str(e)}")
        return {"supported": False, "error": str(e)}
    
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)