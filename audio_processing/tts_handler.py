import os
import tempfile
import logging
from typing import Optional, Dict, Any
import io
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = os.getenv('BASE_URL')
class TTSHandler:
    """Handles Text-to-Speech conversion using OpenAI TTS API"""

    def __init__(self):
        """Initialize TTS handler with OpenAI configuration"""
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('API_KEY')
        self.api_url = f"{BASE_URL}/audio/speech"
        self.model = "tts-1"
        self.voice = "alloy"  
        self.speed = 1.0      
        self.max_text_length = 4000 
        
        if not self.api_key:
            self.logger.warning("OpenAI API key not found. TTS functionality will be disabled.")
        
        self.logger.info("TTSHandler initialized with OpenAI TTS-1")

    def text_to_speech(self, text: str, slow: bool = False) -> Dict[str, Any]:
        """
        Convert text to speech using OpenAI TTS API
        
        Args:
            text (str): Text to convert to speech
            slow (bool): Whether to use slower speech rate (optional)
            
        Returns:
            Dict containing success status, audio data, and metadata
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "OpenAI API key not configured",
                    "audio_data": None,
                    "language": "en"
                }

            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "No text provided for TTS conversion",
                    "audio_data": None,
                    "language": "en"
                }

            cleaned_text = self._clean_text(text)
            if not cleaned_text:
                return {
                    "success": False,
                    "error": "Text is empty after cleaning",
                    "audio_data": None,
                    "language": "en"
                }

            # Adjust speed if slow is requested
            current_speed = 0.8 if slow else self.speed

            self.logger.info(f"Converting text to speech: '{cleaned_text[:50]}...' (Length: {len(cleaned_text)})")


            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "input": cleaned_text,
                "voice": self.voice,
                "speed": current_speed
            }


            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30 
            )

            if response.status_code == 200:
                audio_data = response.content
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                self.logger.info(f"TTS conversion successful. Audio size: {len(audio_data)} bytes")

                return {
                    "success": True,
                    "audio_data": audio_base64,
                    "audio_bytes": audio_data,  # Keep raw bytes for file operations
                    "language": "en", 
                    "format": "mp3",
                    "text_length": len(cleaned_text),
                    "error": None
                }
            else:
                error_msg = f"OpenAI API error: {response.status_code}"
                try:
                    error_detail = response.json().get("error", {}).get("message", "Unknown error")
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "audio_data": None,
                    "language": "en"
                }

        except requests.exceptions.Timeout:
            error_msg = "OpenAI API request timed out"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "audio_data": None,
                "language": "en"
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"OpenAI API request failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "audio_data": None,
                "language": "en"
            }
        except Exception as e:
            self.logger.error(f"TTS conversion failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"TTS conversion failed: {str(e)}",
                "audio_data": None,
                "language": "en"
            }

    def _clean_text(self, text: str) -> str:
        """
        Clean text for TTS conversion
        
        Args:
            text (str): Raw text to clean
            
        Returns:
            str: Cleaned text suitable for TTS
        """
        if not text:
            return ""

        import re
        
        # Remove code blocks and inline code
        text = re.sub(r'```[\s\S]*?```', '[code block]', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'#{1,6}\s*(.*)', r'\1', text)  # Headers
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[link]', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Truncate if too long (OpenAI limit is 4096 characters)
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length] + "..."
            self.logger.warning(f"Text truncated to {self.max_text_length} characters for TTS")

        return text

    def create_temp_audio_file(self, audio_data: bytes, format: str = "mp3") -> str:
        """
        Create temporary audio file from bytes data
        
        Args:
            audio_data (bytes): Audio file data
            format (str): Audio format (mp3)
            
        Returns:
            str: Path to temporary file
        """
        try:
            suffix = f".{format}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_data)
                return temp_file.name
        except Exception as e:
            self.logger.error(f"Failed to create temp audio file: {str(e)}")
            return None

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get dictionary of supported languages
        
        Returns:
            Dict mapping language codes to language names (English only)
        """
        return {'en': 'English'}

    def is_language_supported(self, language: str) -> bool:
        """
        Check if a language is supported
        
        Args:
            language (str): Language code to check
            
        Returns:
            bool: True if language is English
        """
        return language.lower() in ['en', 'english']

    def is_api_configured(self) -> bool:
        """
        Check if OpenAI API is properly configured
        
        Returns:
            bool: True if API key is available
        """
        return bool(self.api_key)

    @staticmethod
    def cleanup_temp_file(file_path: str) -> None:
        """
        Safely remove temporary file
        
        Args:
            file_path (str): Path to file to remove
        """
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")


tts_handler = TTSHandler()