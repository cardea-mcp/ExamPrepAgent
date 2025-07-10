#!/bin/bash

# Download gaia-mcp-servers for your platform
echo "📥 Downloading gaia-mcp-servers..."

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [[ $(uname -m) == "aarch64" ]]; then
        PLATFORM="linux-unknown-gnu-aarch64"
    else
        PLATFORM="linux-unknown-gnu-x86_64"
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

# Download and extract
curl -LO "https://github.com/decentralized-mcp/gaia-mcp-servers/releases/latest/download/gaia-mcp-servers-${PLATFORM}.tar.gz"

if [ $? -eq 0 ]; then
    echo "✅ Downloaded gaia-mcp-servers-${PLATFORM}.tar.gz"
    
    # Extract
    tar -xzf "gaia-mcp-servers-${PLATFORM}.tar.gz"
    
    # Make executable
    chmod +x gaia-tidb-mcp-server
    
    echo "✅ Extracted and configured gaia-tidb-mcp-server"
    echo "📍 Binary location: $(pwd)/gaia-tidb-mcp-server"
else
    echo "❌ Failed to download gaia-mcp-servers"
    exit 1
fi

# Create start script
cat > start_tidb_mcp.sh << 'EOF'
#!/bin/bash

# Load environment variables
source .env

# Set logging
export RUST_LOG=debug
export LLAMA_LOG=debug

# Start TiDB MCP Server
echo "🚀 Starting TiDB MCP Server on port 9096..."

./gaia-tidb-mcp-server \
    --socket-addr 127.0.0.1:9096 \
    --transport stream-http \
    --ssl-ca /etc/ssl/certs/ca-certificates.crt \
    --database "${TIDB_DATABASE}" \
    --table-name "knowledge_base" \
    --search-tool-desc "You MUST call the search() tool before answering any factual question. For practice questions, search with difficulty/topic keywords like 'beginner kubernetes'. For specific questions, extract keywords from the user query and search for relevant information." \
    --search-tool-param-desc "Keywords or phrase to search for. Use difficulty/topic terms for practice questions (e.g., 'beginner networking') or question keywords for specific queries (e.g., 'kubernetes pod definition')."

EOF

chmod +x start_tidb_mcp.sh

echo "✅ Created start_tidb_mcp.sh script"
echo "🔧 Configuration complete!"