# audio_processing/audio_utils.py
import os
import tempfile
import mimetypes
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Supported audio MIME types
SUPPORTED_AUDIO_TYPES = {
    'audio/mpeg',           # MP3
    'audio/wav',            # WAV
    'audio/x-wav',          # WAV alternative
    'audio/mp4',            # M4A
    'audio/m4a',            # M4A alternative
    'audio/ogg',            # OGG
    'audio/webm',           # WebM
    'video/webm',           # WebM video (for audio)
    'audio/flac',           # FLAC
}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

def validate_audio_file(file_data: bytes, filename: str, content_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate audio file data
    
    Args:
        file_data (bytes): Audio file data
        filename (str): Original filename
        content_type (str, optional): Content type from upload
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Check file size
        if len(file_data) > MAX_FILE_SIZE:
            return False, f"File size too large. Maximum allowed: {MAX_FILE_SIZE // (1024*1024)}MB"
        
        if len(file_data) == 0:
            return False, "Empty file uploaded"
        
        # Check file extension
        file_ext = get_file_extension(filename).lower()
        if file_ext not in ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac']:
            return False, f"Unsupported file format: {file_ext}"
        
        # Check MIME type if provided
        if content_type and content_type not in SUPPORTED_AUDIO_TYPES:
            # Try to guess MIME type from filename
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type not in SUPPORTED_AUDIO_TYPES:
                return False, f"Unsupported audio format: {content_type}"
        
        # Basic file validation - check for common audio file signatures
        if not _has_valid_audio_signature(file_data, file_ext):
            return False, "File does not appear to be a valid audio file"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating audio file: {str(e)}")
        return False, f"Validation error: {str(e)}"

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    if '.' in filename:
        return '.' + filename.split('.')[-1].lower()
    return ''

def _has_valid_audio_signature(file_data: bytes, file_ext: str) -> bool:
    """
    Check if file has valid audio signature
    
    Args:
        file_data (bytes): File data to check
        file_ext (str): File extension
    
    Returns:
        bool: True if file appears to be valid audio
    """
    if len(file_data) < 12:
        return False

    if file_ext == '.mp3':
        return (file_data[:3] == b'ID3' or 
                file_data[:2] == b'\xff\xfb' or 
                file_data[:2] == b'\xff\xfa')
    
    elif file_ext == '.wav':
        return (file_data[:4] == b'RIFF' and 
                file_data[8:12] == b'WAVE')
    
    elif file_ext in ['.m4a', '.mp4']:
        return b'ftyp' in file_data[:32]
    
    elif file_ext == '.ogg':
        # OGG files start with OggS
        return file_data[:4] == b'OggS'
    
    elif file_ext == '.webm':
        # WebM files start with EBML signature
        return file_data[:4] == b'\x1a\x45\xdf\xa3'
    
    elif file_ext == '.flac':
        # FLAC files start with fLaC
        return file_data[:4] == b'fLaC'
    
    # If we can't verify signature, assume it's valid
    return True

def create_temp_audio_file(file_data: bytes, filename: str) -> str:
    """
    Create temporary audio file from bytes data
    
    Args:
        file_data (bytes): Audio file data
        filename (str): Original filename for extension
    
    Returns:
        str: Path to temporary file
    """
    file_ext = get_file_extension(filename)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        temp_file.write(file_data)
        return temp_file.name

def cleanup_temp_file(file_path: str) -> None:
    """
    Safely remove temporary file
    
    Args:
        file_path (str): Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")

def get_audio_duration_estimate(file_size: int) -> float:
    """
    Estimate audio duration based on file size (rough approximation)
    
    Args:
        file_size (int): File size in bytes
    
    Returns:
        float: Estimated duration in seconds
    """
    # Very rough estimate: 1MB ≈ 1 minute for typical compressed audio
    return (file_size / (1024 * 1024)) * 60