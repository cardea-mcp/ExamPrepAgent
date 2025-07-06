#!/bin/bash

echo "🚀 Starting ExamBOT with Llama-Nexus..."

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=${3:-30}
    
    echo "⏳ Waiting for $service_name to be ready..."
    
    for i in $(seq 1 $max_attempts); do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        if [ $i -eq $max_attempts ]; then
            echo "❌ Timeout waiting for $service_name"
            return 1
        fi
        
        sleep 2
    done
}

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    if [ ! -z "$MCP_PID" ]; then
        echo "Stopping TiDB MCP Server (PID: $MCP_PID)..."
        kill $MCP_PID 2>/dev/null
    fi
    
    if [ ! -z "$NEXUS_PID" ]; then
        echo "Stopping Llama-Nexus (PID: $NEXUS_PID)..."
        kill $NEXUS_PID 2>/dev/null
    fi
    
    # Kill any remaining processes
    pkill -f "gaia-tidb-mcp-server" 2>/dev/null
    pkill -f "llama-nexus" 2>/dev/null
    
    echo "✅ Cleanup completed"
    exit 0
}

# Set up signal handlers for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Check if required files exist
echo "🔍 Checking required files..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.template"
    exit 1
fi

if [ ! -f "gaia-tidb-mcp-server" ]; then
    echo "❌ gaia-tidb-mcp-server not found. Run setup_complete_system.sh first"
    exit 1
fi

if [ ! -f "./nexus/llama-nexus" ]; then
    echo "❌ llama-nexus not found. Run setup_complete_system.sh first"
    exit 1
fi

if [ ! -f "app_nexus.py" ]; then
    echo "❌ app_nexus.py not found. Please ensure the migration is complete"
    exit 1
fi

echo "✅ All required files found"

# Step 1: Start TiDB MCP Server
echo ""
echo "🔧 Step 1: Starting TiDB MCP Server..."

nohup bash start_tidb_mcp.sh > mcp_server.log 2>&1 &
MCP_PID=$!
echo "TiDB MCP Server started with PID: $MCP_PID"

# Wait for MCP server to be ready
sleep 5

# Step 2: Start Llama-Nexus
echo ""
echo "🔧 Step 2: Starting Llama-Nexus..."

nohup bash start_llama_nexus.sh > nexus.log 2>&1 &
NEXUS_PID=$!
echo "Llama-Nexus started with PID: $NEXUS_PID"

# Wait for Llama-Nexus to be ready
if ! wait_for_service "http://localhost:9095/health" "Llama-Nexus" 30; then
    echo "❌ Llama-Nexus failed to start. Check nexus.log for details:"
    tail -n 20 nexus.log
    exit 1
fi

# Step 3: Register API servers
echo ""
echo "🔧 Step 3: Registering API servers..."

if bash register_apis.sh; then
    echo "✅ API servers registered successfully"
else
    echo "❌ Failed to register API servers"
    exit 1
fi

# Step 4: Start the main application
echo ""
echo "🚀 Step 4: Starting ExamBOT application..."
echo ""
echo "✅ System started successfully!"
echo ""
echo "📍 Service URLs:"
echo "  - TiDB MCP Server: http://localhost:9096"
echo "  - Llama-Nexus: http://localhost:9095"
echo "  - ExamBOT App: http://localhost:8000"
echo ""
echo "📊 Logs:"
echo "  - MCP Server: mcp_server.log"
echo "  - Llama-Nexus: nexus.log"
echo ""
echo "🎯 Starting ExamBOT application now..."
echo "   (Press Ctrl+C to stop all services)"
echo ""

# Start the main application (this will run in foreground)
python app_nexus.py