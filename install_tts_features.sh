#!/bin/bash
# install_tts_features.sh

echo "Installing Text-to-Speech dependencies..."

# Install Python dependencies
pip install gtts pydub

echo "Text-to-Speech installation complete!"
echo "You can now use voice responses in the application"