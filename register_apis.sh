#!/bin/bash

echo "📝 Registering API servers with llama-nexus..."

# Wait for llama-nexus
for i in {1..30}; do
    if curl -s http://localhost:9095/health > /dev/null 2>&1; then
        echo "✅ Llama-nexus is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Timeout waiting for llama-nexus"
        exit 1
    fi
    sleep 1
done

# Register chat API
curl --silent --location 'http://localhost:9095/admin/servers/register' \
--header 'Content-Type: application/json' \
--data '{
    "url": "https://0xb2962131564bc854ece7b0f7c8c9a8345847abfb.gaia.domains",
    "kind": "chat"
}'

echo "✅ Chat API server registered"

# Register embedding API
curl --silent --location 'http://localhost:9095/admin/servers/register' \
--header 'Content-Type: application/json' \
--data '{
    "url": "https://0x448f0405310a9258cd5eab5f25f15679808c5db2.gaia.domains",
    "kind": "embeddings"
}'

echo "✅ Embedding API server registered"
echo "✅ All API servers registered successfully!"
