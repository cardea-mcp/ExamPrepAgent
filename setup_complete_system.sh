#!/bin/bash

echo "🚀 Setting up ExamBOT with Llama-Nexus"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables properly
echo "🔧 Loading environment variables..."
set -a
source .env
set +a

# Verify essential variables are loaded
if [ -z "$TIDB_HOST" ] || [ -z "$TIDB_USERNAME" ] || [ -z "$TIDB_PASSWORD" ] || [ -z "$TIDB_DATABASE" ]; then
    echo "❌ Missing required TiDB environment variables. Please check your .env file."
    exit 1
fi

echo "✅ Environment variables loaded"


# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [[ $(uname -m) == "aarch64" ]]; then
        PLATFORM="unknown-linux-gnu-aarch64"
    else
        PLATFORM="unknown-linux-gnu-x86_64"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ $(uname -m) == "arm64" ]]; then
        PLATFORM="darwin-aarch64"
    else
        PLATFORM="darwin-x86_64"
    fi
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi


# Step 3: Download and setup Llama-Nexus
echo "🔧 Step 1: Setting up Llama-Nexus..."

if [ ! -d "./nexus" ] || [ ! -f "./nexus/llama-nexus" ]; then
    echo "📥 Downloading llama-nexus..."
    mkdir -p ./nexus
    curl -LO "https://github.com/LlamaEdge/llama-nexus/releases/download/0.5.0/llama-nexus-${PLATFORM}.tar.gz"

    if [ $? -eq 0 ]; then
        echo "✅ Downloaded llama-nexus"
        mv "llama-nexus-${PLATFORM}.tar.gz" "./nexus/"
        cd ./nexus
        tar -xzf "llama-nexus-${PLATFORM}.tar.gz"
        rm "llama-nexus-${PLATFORM}.tar.gz"
        cd ..

        echo "✅ Extracted llama-nexus to ./nexus/"
    else
        echo "❌ Failed to download llama-nexus"
        exit 1
    fi
else
    echo "✅ llama-nexus already exists at ./nexus/llama-nexus"
fi


