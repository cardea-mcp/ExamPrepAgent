from fastmcp import Client
from dotenv import load_dotenv
import os
load_dotenv()

MCP_PORT = os.getenv('MCP_PORT')
MCP_HOST = os.getenv('MCP_HOST')
url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
client = Client(url)