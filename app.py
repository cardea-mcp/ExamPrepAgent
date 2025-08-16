from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from llm_api import cleanup_server,process_audio_message_with_context,process_message_with_context
from audio_processing.whisper_handler import whisper_handler 
from audio_processing.audio_utils import validate_audio_file, MAX_FILE_SIZE, get_file_extension, cleanup_temp_file
from audio_processing.tts_handler import tts_handler
import atexit
import logging
import tempfile 
import ffmpeg
import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

host = os.getenv('HOST', '0.0.0.0')
port = int(os.getenv('PORT', 8000))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ExamBOT API")



atexit.register(cleanup_server)

app.mount("/static", StaticFiles(directory="static"), name="static")



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

@app.post("/api/tts")
async def text_to_speech_endpoint(
    request: dict
):
    """Convert text to speech"""
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        slow = request.get("slow", False)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = tts_handler.text_to_speech(text)
        
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
            "supported": tts_handler.is_api_configured(),  
            "languages": tts_handler.get_supported_languages(),
            "default_language": "en" 
        }
    except Exception as e:
        logger.error(f"TTS support check failed: {str(e)}")
        return {"supported": False, "error": str(e)}
    
# Add this new endpoint after the existing ones in app.py

@app.post("/api/chat/message")
async def process_chat_message(request: dict):
    """
    Process a single message with provided context
    """
    try:
        user_message = request.get("message", "").strip()
        conversation_context = request.get("context", [])
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Process the message with the provided context
        response_data = await process_message_with_context(user_message, conversation_context)
        
        return {
            "success": True,
            "response": response_data["response_text"],
            "tool_calls": response_data.get("tool_calls"),
            "tool_responses": response_data.get("tool_responses"),
            "assistant_content": response_data.get("assistant_content"),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/audio")
async def process_chat_audio(
    audio_file: UploadFile = File(...),
    context: str = None,
    language: Optional[str] = None
):
    """
    Process audio message with provided context
    """
    temp_input_file_path = None
    temp_wav_file_path = None

    try:
        # Parse context from form data
        conversation_context = []
        if context:
            try:
                conversation_context = json.loads(context)
            except json.JSONDecodeError:
                conversation_context = []

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
        if not original_ext:
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

        # Process audio with context
        response = await process_audio_message_with_context(
            wav_contents,
            os.path.basename(temp_wav_file_path),
            conversation_context,
            language
        )
        
        if response.get("success") and response.get("response"):
            detected_lang = response.get("detected_language", "en")
            tts_lang = detected_lang if tts_handler.is_language_supported(detected_lang) else "en"
            
            tts_result = tts_handler.text_to_speech(response["response"])
            
            if tts_result["success"]:
                response["tts_audio"] = tts_result["audio_data"]
                response["tts_format"] = tts_result["format"]
            else:
                logger.warning(f"TTS generation failed: {tts_result['error']}")
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing error in endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    finally:
        if temp_input_file_path:
            cleanup_temp_file(temp_input_file_path)
        if temp_wav_file_path:
            cleanup_temp_file(temp_wav_file_path)    
    
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)