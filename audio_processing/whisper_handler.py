import os
import re
import tempfile
import logging
from typing import Optional, Dict, Any
import io 
import requests 
from dotenv import load_dotenv

load_dotenv() 


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


OPENAI_API_URL = "http://localhost:8080/v1/audio/transcriptions"

def clean_transcription_timestamps(text_with_timestamps: str) -> str:
    """
    Removes Whisper-style timestamps like "[00:00:00.000 --> 00:00:07.080] "
    and leading/trailing newlines/spaces.
    It also handles cases where multiple segments might be on new lines.
    """
    if not text_with_timestamps:
        return ""

    lines = text_with_timestamps.splitlines()
    cleaned_lines = []
    for line in lines:
        # Remove the timestamp pattern from the beginning of the line
        cleaned_line = re.sub(r'^\[\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*\]\s*', '', line)
        if cleaned_line.strip(): # Add line only if it's not empty after cleaning
            cleaned_lines.append(cleaned_line.strip())
    
    return " ".join(cleaned_lines).strip()
class WhisperHandler:
    """Handles audio transcription via a local or OpenAI-compatible API"""

    def __init__(self):
        """
        Initialize API handler
        """
        self.logger = logging.getLogger(__name__)
        # You might want a specific check or info log if you are targeting a local server
        self.logger.info(f"WhisperHandler initialized to target API endpoint: {OPENAI_API_URL}")

    # def load_model(self) -> bool:
    #     """
    #     For a local server not requiring an API key, this can always return True
    #     or check for some other configuration if needed.
    #     If you still want to gate functionality on OPENAI_API_KEY for some reason, keep the check.
    #     Assuming for now the local server is always "available" if reachable.
    #     """
    #     self.logger.info(f"Transcription will use API endpoint: {OPENAI_API_URL}")

    #     return True

    def _make_api_call(self, audio_file_obj, filename: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Internal method to make the API call.
        """
        headers = {}
        files_payload = {
            'file': (filename, audio_file_obj, 'application/octet-stream'), # 'application/octet-stream' is a safe default
        }


        # if language:
        #     files_payload['language'] = (None, language) # Add if your local API supports it

        try:
            self.logger.info(f"Sending audio data to API for transcription. Endpoint: {OPENAI_API_URL}, Filename: {filename}")
            response = requests.post(OPENAI_API_URL, headers=headers, files=files_payload, timeout=60)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            
            result = response.json()
            raw_transcribed_text = result.get("text", "").strip() # Get the raw text

            # Clean the timestamps from the raw text
            cleaned_transcribed_text = clean_transcription_timestamps(raw_transcribed_text)
            
            detected_language = result.get("language", "unknown")

            self.logger.info(f"Transcription successful via API. Raw: '{raw_transcribed_text[:100]}...', Cleaned: '{cleaned_transcribed_text[:100]}...'")
            return {
                "success": True,
                "text": cleaned_transcribed_text, 
                "language": detected_language,
                "error": None
            }

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_content = e.response.json()
                    if isinstance(error_content, dict) and "error" in error_content:
                        if isinstance(error_content["error"], dict):
                             error_detail = error_content["error"].get("message", str(e))
                        else:
                             error_detail = str(error_content["error"])
                    else: 
                        error_detail = e.response.text 
                except ValueError:
                    error_detail = e.response.text
            return {
                "success": False,
                "error": f"API Error: {error_detail}",
                "text": "",
                "language": None
            }
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during API transcription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "language": None
            }

    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file to text using the configured API.
        """
        if not self.load_model(): 
            return {
                "success": False,
                "error": "Transcription handler not properly loaded/configured.", # Generic message
                "text": "",
                "language": None
            }

        if not os.path.exists(audio_file_path):
            return {
                "success": False,
                "error": "Audio file not found",
                "text": "",
                "language": None
            }

        filename = os.path.basename(audio_file_path)
        try:
            with open(audio_file_path, 'rb') as audio_file:
                return self._make_api_call(audio_file, filename, language)
        except IOError as e:
            self.logger.error(f"Could not open audio file {audio_file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"File IO Error: {str(e)}",
                "text": "",
                "language": None
            }

    def transcribe_audio_bytes(self, audio_data: bytes, filename: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio from bytes data using the configured API.
        """
        # if not self.load_model():
        #     return {
        #         "success": False,
        #         "error": "Transcription handler not properly loaded/configured.",
        #         "text": "",
        #         "language": None
        #     }

        if not audio_data:
             return {
                "success": False,
                "error": "No audio data provided",
                "text": "",
                "language": None
            }

        audio_file_obj = io.BytesIO(audio_data)
        return self._make_api_call(audio_file_obj, filename, language)

    def get_supported_formats(self) -> list:
        """
        Get list of supported audio formats by the target API.
        Assuming similar to OpenAI for now, adjust if your local API has different support.
        """
        return ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.flac'] 

    def is_model_loaded(self) -> bool:
        """
        This method's meaning changes. For a local server, it might mean "is configured".
        If you still want to gate on OPENAI_API_KEY for some reason (e.g. if it's a general purpose key):
        # return OPENAI_API_KEY is not None
        For a local server with no auth, it's always "loaded" in terms of API key.
        """
        return True 

whisper_handler = WhisperHandler()