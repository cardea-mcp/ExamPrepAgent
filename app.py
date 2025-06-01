from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database.monogodb import MongoDB
from llm_api import initialize_mcp_server, process_message, cleanup_server, process_audio_message
from audio_processing.whisper_handler import whisper_handler 
from audio_processing.audio_utils import validate_audio_file, MAX_FILE_SIZE, get_file_extension, cleanup_temp_file
import atexit
import logging
import tempfile 
import ffmpeg
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ExamBOT API")

mongo_db = MongoDB()
available_functions = initialize_mcp_server()

atexit.register(cleanup_server)


app.mount("/static", StaticFiles(directory="static"), name="static")


class UserCreate(BaseModel):
    name: str

class MessageSend(BaseModel):
    message: str

class SessionCreate(BaseModel):
    name: Optional[str] = None

class SessionUpdate(BaseModel):
    name: str


def transcode_to_wav(input_file_path: str, output_file_path: str) -> bool:
    """
    Transcodes an audio file to WAV (PCM 16-bit) using ffmpeg.
    Returns True on success, False on failure.
    """
    try:
        logger.info(f"Transcoding '{input_file_path}' to WAV at '{output_file_path}'")
        (
            ffmpeg
            .input(input_file_path)
            .output(output_file_path, format='wav', acodec='pcm_s16le', ar='16000', ac=1) # PCM 16-bit LE, 16kHz, Mono
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"Transcoding successful: '{output_file_path}'")
        return True
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg transcoding error for {input_file_path}:")
        logger.error(f"FFmpeg stdout: {e.stdout.decode('utf8')}")
        logger.error(f"FFmpeg stderr: {e.stderr.decode('utf8')}")
        return False
    except Exception as e_gen:
        logger.error(f"Unexpected error during transcoding of {input_file_path}: {str(e_gen)}")
        return False


# Existing API Routes...
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

@app.post("/api/sessions/{session_id}/messages")
async def send_message_route(session_id: str, message: MessageSend): 
    try:
        response = await process_message(session_id, message.message, available_functions)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/audio")
async def send_audio_message_route( 
    session_id: str,
    audio_file: UploadFile = File(...),
    language: Optional[str] = None
):
    """Send an audio message to the chatbot, with transcoding to WAV."""
    temp_input_file_path = None
    temp_wav_file_path = None

    try:
        # Validate file size
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

            logger.warning(f"Initial audio validation failed for '{original_filename}': {error_message}. Attempting transcoding anyway.")


        # Save uploaded audio to a temporary file
        original_ext = get_file_extension(original_filename)
        if not original_ext: # if no extension, default to .webm as browser likely sends that
            original_ext = ".webm"
            original_filename += original_ext

        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_in:
            tmp_in.write(contents)
            temp_input_file_path = tmp_in.name
        
        logger.info(f"Received audio file: '{original_filename}', saved to temp: '{temp_input_file_path}'")

       
        temp_wav_file_path = tempfile.mktemp(suffix=".wav")

        # Transcode to WAV
        transcode_success = transcode_to_wav(temp_input_file_path, temp_wav_file_path)
        if not transcode_success:
            raise HTTPException(status_code=500, detail="Audio transcoding to WAV failed.")

        # Read the transcoded WAV file data
        with open(temp_wav_file_path, 'rb') as f_wav:
            wav_contents = f_wav.read()

        # Process audio (now WAV) and get response
        # The filename passed to process_audio_message should now reflect it's a WAV file
        response = await process_audio_message(
            session_id,
            wav_contents, # Send WAV bytes
            os.path.basename(temp_wav_file_path), # e.g., "somerandomname.wav"
            available_functions,
            language
        )
        
        return response

    except HTTPException:
        raise # Re-raise HTTPException if it's already one
    except Exception as e:
        logger.error(f"Audio processing error in endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    finally:
        # Clean up temporary files
        if temp_input_file_path:
            cleanup_temp_file(temp_input_file_path)
        if temp_wav_file_path:
            cleanup_temp_file(temp_wav_file_path)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    # ... (implementation)
    success = mongo_db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}

@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    # ... (implementation)
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
            "model_info": f"Transcription API (e.g., local Llama or OpenAI) - Key Set: {api_key_is_set}",
            "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
            "supported_formats": whisper_handler.get_supported_formats() 
        }
    except Exception as e:
        logger.error(f"Audio support check failed: {str(e)}")
        return { "supported": False, "error": str(e) }


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    # ... (implementation)
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)