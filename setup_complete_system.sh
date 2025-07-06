#!/bin/bash

echo "🚀 Setting up ExamBOT with Llama-Nexus and TiDB MCP..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.template"
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

# Step 1: Setup knowledge base from CSV
echo "📊 Step 1: Setting up knowledge base from CSV..."
python database/csv_loader.py

if [ $? -ne 0 ]; then
    echo "❌ Knowledge base setup failed!"
    exit 1
fi

# Step 2: Download and setup MCP server
echo "🔧 Step 2: Setting up TiDB MCP server..."

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

# Download MCP server if not exists
if [ ! -f "gaia-tidb-mcp-server" ]; then
    echo "📥 Downloading gaia-mcp-servers..."
    curl -LO "https://github.com/decentralized-mcp/gaia-mcp-servers/releases/latest/download/gaia-mcp-servers-${PLATFORM}.tar.gz"

    if [ $? -eq 0 ]; then
        echo "✅ Downloaded gaia-mcp-servers"
        tar -xzf "gaia-mcp-servers-${PLATFORM}.tar.gz"
        chmod +x gaia-tidb-mcp-server
        rm "gaia-mcp-servers-${PLATFORM}.tar.gz"
    else
        echo "❌ Failed to download gaia-mcp-servers"
        exit 1
    fi
else
    echo "✅ gaia-tidb-mcp-server already exists"
fi

# Create MCP server start script
cat > start_tidb_mcp.sh << 'EOF'
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
    --socket-addr 127.0.0.1:9096 \
    --transport stream-http \
    --database "${TIDB_DATABASE}" \
    --table-name "kubernetes_qa_pairs" \
    --search-tool-desc "You MUST call the search() tool before answering any factual question. For practice questions, search with difficulty/topic keywords like 'beginner kubernetes'. For specific questions, extract keywords from the user query and search for relevant information." \
    --search-tool-param-desc "Keywords or phrase to search for. Use difficulty/topic terms for practice questions (e.g., 'beginner networking') or question keywords for specific queries (e.g., 'kubernetes pod definition')."
EOF

chmod +x start_tidb_mcp.sh

# Step 3: Download and setup Llama-Nexus
echo "🔧 Step 3: Setting up Llama-Nexus..."

if [ ! -d "./nexus" ] || [ ! -f "./nexus/llama-nexus" ]; then
    echo "📥 Downloading llama-nexus..."
    mkdir -p ./nexus
    curl -LO "https://github.com/LlamaEdge/llama-nexus/releases/latest/download/llama-nexus-${PLATFORM}.tar.gz"

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

# Create Llama-Nexus config
cat > config.toml << 'EOF'
[server]
host = "0.0.0.0"
port = 9095

[[mcp.server.tool]]
name      = "gaia-tidb-search"
transport = "stream-http"
url       = "http://127.0.0.1:9096/mcp"
enable    = true
EOF

# Create Llama-Nexus start script
cat > start_llama_nexus.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting llama-nexus on port 9095..."


if [ ! -f "./nexus/llama-nexus" ]; then
    echo "❌ llama-nexus binary not found!"
    exit 1
fi

./nexus/llama-nexus --config ./nexus/config.toml
EOF

chmod +x start_llama_nexus.sh

# Create API registration script
cat > register_apis.sh << 'EOF'
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
    "url": "https://0x9fcf7888963793472bfcb8c14f4b6b47a7462f17.gaia.domains",
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
EOF

chmod +x register_apis.sh

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Start the system: bash start_system.sh"
echo "2. Your CSV data is now loaded in the knowledge_base table"
echo "3. Access your application at: http://localhost:8000"