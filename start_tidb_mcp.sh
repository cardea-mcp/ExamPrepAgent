#!/bin/bash

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found!"
    exit 1
fi

# Start TiDB MCP Server
echo "🚀 Starting agentic search MCP Server on port 9096..."

./gaia-agentic-search-mcp-server tidb \
    --tidb-ssl-ca /etc/ssl/certs/ca-certificates.crt \
    --tidb-table-name kubernetes_qa_pairs \
    --chat-service https://0xb2962131564bc854ece7b0f7c8c9a8345847abfb.gaia.domains \
    --limit 8 \
    --score-threshold 0.5
