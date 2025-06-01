# audio_processing/whisper_handler.py
import whisper
import os
import tempfile
import logging
from typing import Optional, Dict, Any
import torch

class WhisperHandler:
    """Handles Whisper model loading and audio transcription"""
    
    def __init__(self, model_size: str = "base.en"):
        """
        Initialize Whisper handler
        
        Args:
            model_size (str): Size of the Whisper model to use ("tiny", "base", "small", "medium", "large")
        """
        self.model_size = model_size
        self.model = None
        self.logger = logging.getLogger(__name__)
        
    def load_model(self) -> bool:
        """
        Load the Whisper model
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            if self.model is None:
                self.logger.info(f"Loading Whisper model: {self.model_size}")
                
                # Check if CUDA is available for faster processing
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.logger.info(f"Using device: {device}")
                
                # Load the model
                self.model = whisper.load_model(self.model_size, device=device)
                self.logger.info("Whisper model loaded successfully")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {str(e)}")
            return False
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en', 'es', 'fr')
        
        Returns:
            Dict containing transcription result and metadata
        """
        try:
            # Ensure model is loaded
            if not self.load_model():
                return {
                    "success": False,
                    "error": "Failed to load Whisper model",
                    "text": "",
                    "language": None
                }
            
            # Check if file exists
            if not os.path.exists(audio_file_path):
                return {
                    "success": False,
                    "error": "Audio file not found",
                    "text": "",
                    "language": None
                }
            
            self.logger.info(f"Starting transcription of: {audio_file_path}")
            
            # Perform transcription
            options = {}
            if language:
                options["language"] = language
            
            result = self.model.transcribe(audio_file_path, **options)
            
            self.logger.info("Transcription completed successfully")
            
            return {
                "success": True,
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "language": None
            }
    
    def transcribe_audio_bytes(self, audio_data: bytes, filename: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio from bytes data
        
        Args:
            audio_data (bytes): Audio file data in bytes
            filename (str): Original filename for extension detection
            language (str, optional): Language code
        
        Returns:
            Dict containing transcription result and metadata
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(filename)) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe the temporary file
            result = self.transcribe_audio(temp_file_path, language)
            
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass  # Ignore cleanup errors
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to transcribe audio bytes: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "language": None
            }
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        return '.wav'  # Default extension
    
    def get_supported_formats(self) -> list:
        """Get list of supported audio formats"""
        return ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.avi', '.mov']
    
    def is_model_loaded(self) -> bool:
        """Check if model is currently loaded"""
        return self.model is not None

# Global instance to be reused across requests
whisper_handler = WhisperHandler(model_size="base.en")