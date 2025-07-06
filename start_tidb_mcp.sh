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
echo "🚀 Starting TiDB MCP Server on port 9096..."

./gaia-tidb-mcp-server \
    --ssl-ca /etc/ssl/certs/ca-certificates.crt \
    --socket-addr 127.0.0.1:9096 \
    --transport stream-http \
    --database "${TIDB_DATABASE}" \
    --table-name "kubernetes_qa_pairs" \
    --search-tool-desc "You MUST call the search() tool before answering any factual question. For practice questions, search with difficulty/topic keywords like 'beginner kubernetes'. For specific questions, extract keywords from the user query and search for relevant information." \
    --search-tool-param-desc "Keywords or phrase to search for. Use difficulty/topic terms for practice questions (e.g., 'beginner networking') or question keywords for specific queries (e.g., 'kubernetes pod definition')."
