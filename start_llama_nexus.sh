#!/bin/bash

echo "🚀 Starting llama-nexus on port 9095..."


if [ ! -f "./nexus/llama-nexus" ]; then
    echo "❌ llama-nexus binary not found!"
    exit 1
fi

./nexus/llama-nexus --config ./nexus/config.toml
