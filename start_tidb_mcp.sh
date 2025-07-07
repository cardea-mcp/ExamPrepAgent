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

./gaia-agentic-search-mcp-server --socket-addr 127.0.0.1:9096 --transport stream-http --search-tool-desc "You MUST call the search() tool before you answer any factual question. Create a question from the user query and relevant context, and pass the question as a string to the tool call." --search-tool-param-desc "The keyword to search for answers." tidb \
    --tidb-ssl-ca /etc/ssl/certs/ca-certificates.crt \
    --tidb-table-name my_table \
    --chat-service https://0xb2962131564bc854ece7b0f7c8c9a8345847abfb.gaia.domains \
    --limit 10 \
    --score-threshold 0.5