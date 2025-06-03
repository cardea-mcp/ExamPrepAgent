import os
import tempfile
import logging
from typing import Optional, Dict, Any
import io
import base64
from gtts import gTTS

logger = logging.getLogger(__name__)

class TTSHandler:
    """Handles Text-to-Speech conversion using gTTS"""

    def __init__(self):
        """Initialize TTS handler"""
        self.logger = logging.getLogger(__name__)
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese'
        }
        self.default_language = 'en'
        self.logger.info("TTSHandler initialized")

    def text_to_speech(self, text: str, language: str = None, slow: bool = False) -> Dict[str, Any]:
        """
        Convert text to speech using gTTS
        
        Args:
            text (str): Text to convert to speech
            language (str, optional): Language code (default: 'en')
            slow (bool): Whether to use slow speech rate
            
        Returns:
            Dict containing success status, audio data, and metadata
        """
        try:
            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "No text provided for TTS conversion",
                    "audio_data": None,
                    "language": None
                }

            cleaned_text = self._clean_text(text)
            if not cleaned_text:
                return {
                    "success": False,
                    "error": "Text is empty after cleaning",
                    "audio_data": None,
                    "language": None
                }

            lang = language or self.default_language
            if lang not in self.supported_languages:
                self.logger.warning(f"Unsupported language '{lang}', falling back to English")
                lang = self.default_language

            self.logger.info(f"Converting text to speech: '{cleaned_text[:50]}...' (Language: {lang})")

            tts = gTTS(text=cleaned_text, lang=lang, slow=slow)
            
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            audio_data = audio_buffer.getvalue()

            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            self.logger.info(f"TTS conversion successful. Audio size: {len(audio_data)} bytes")

            return {
                "success": True,
                "audio_data": audio_base64,
                "audio_bytes": audio_data,  # Keep raw bytes for file operations
                "language": lang,
                "format": "mp3",
                "text_length": len(cleaned_text),
                "error": None
            }

        except Exception as e:
            self.logger.error(f"TTS conversion failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"TTS conversion failed: {str(e)}",
                "audio_data": None,
                "language": lang if 'lang' in locals() else None
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
        

        max_length = 1000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            self.logger.warning(f"Text truncated to {max_length} characters for TTS")

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
            Dict mapping language codes to language names
        """
        return self.supported_languages.copy()

    def is_language_supported(self, language: str) -> bool:
        """
        Check if a language is supported
        
        Args:
            language (str): Language code to check
            
        Returns:
            bool: True if language is supported
        """
        return language in self.supported_languages

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