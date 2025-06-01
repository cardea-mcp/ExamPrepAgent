#!/bin/bash
# install_voice_features.sh

echo "Installing voice input dependencies..."

# Install Python dependencies
pip install openai-whisper torch torchaudio ffmpeg-python python-multipart

# Install ffmpeg (system dependency)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing ffmpeg for Linux..."
    sudo apt update && sudo apt install -y ffmpeg
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing ffmpeg for macOS..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "Please install Homebrew first, then run: brew install ffmpeg"
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "For Windows, please install ffmpeg manually:"
    echo "1. Download from https://ffmpeg.org/download.html"
    echo "2. Add to your PATH environment variable"
fi

echo "Voice input installation complete!"
echo "You can now start the application with: python app.py"