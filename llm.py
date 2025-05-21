import json
import subprocess
import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

# Set up your OpenRouter API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with OpenRouter base URL
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
)

# Start the MCP server
server = subprocess.Popen(
    ['python3', 'main.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    stdin=subprocess.PIPE,
    text=True,
)

def create_message(method_name, params, id=None):
    message = {
        "jsonrpc": "2.0",
        "method": method_name,
        "params": params
    }
    if id is not None:
        message["id"] = id
    return json.dumps(message)

def send_message(message):
    server.stdin.write(message + "\n")
    server.stdin.flush()

def receive_message():
    print("Reading from server...")
    # server_output = server.stdout.readline()
    # print("server_output---- \n",server_output)
    server_output = json.loads(server.stdout.readline())
    # print("server_output---- \n",server_output)
    if "result" in server_output:
        return server_output["result"]
    else:
        return "Error"

# Initialize the MCP server connection
id = 1
init_message = create_message(
    "initialize",
    {
        "clientInfo": {
            "name": "Llama Agent",
            "version": "0.1"
        },
        "protocolVersion": "2024-11-05",
        "capabilities": {},
    },
    id
)

print("Sending init message...")
send_message(init_message)
response = receive_message()
server_name = response["serverInfo"]["name"]
print(f"Initializing {server_name}...")

init_complete_message = create_message("notifications/initialized", {})
send_message(init_complete_message)
print("Initialization complete.")

# Get the list of available tools
id += 1
list_tools_message = create_message("tools/list", {}, id)
send_message(list_tools_message)
tools_response = receive_message()

# Format tools for OpenAI API
available_functions = []
for tool in tools_response["tools"]:
    print(f"Found tool: {tool['name']}")
    print(f"Description: {tool['description']}")
    print(f"Parameters: {tool['inputSchema']['properties']}")
    print("")
    
    func = {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "object",
                "properties": tool["inputSchema"]["properties"],
                "required": tool["inputSchema"].get("required", []),
            },
        },
    }
    available_functions.append(func)

# Function to handle tool calls and get responses
def handle_tool_calls(tool_calls):
    tool_responses = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"Calling tool: {function_name} with args: {function_args}")
        
        # Call the MCP tool
        id = tool_call.id  # Use the OpenAI tool call ID
        tool_call_message = create_message("tools/call", {
            "name": function_name,
            "arguments": function_args,
        }, id)
        
        send_message(tool_call_message)
        tool_result = receive_message()
        
        # Extract the result text
        result_text = tool_result["content"][0]["text"] if tool_result.get("content") else "No result"
        
        tool_responses.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": result_text
        })
        
        print(f"Tool response: {tool_responses}")
    
    return tool_responses

# Main interaction loop
def chat_with_exam_bot():
    messages = [
        {"role": "system", "content": "You are a helpful ai assistant. You have two tools that you can access. First is that you can fetch random questions from a file.json. You have to use this tool when the user ask you to give some random question. The other tool is that you can search relevant question and answers related to user question. User can ask some question and you will find the relavant question and answers pair from the dataset, you have a tool to do that. whenever you get some question by user, first search the question in the dataset, if you find the question in the dataset, then return the answer of the question."}
    ]
    
    while True:
        user_input = input("\nYour question (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
            
        # Add user message to conversation
        messages.append({"role": "user", "content": user_input})
        
        # Call OpenAI API with client
        completion = client.chat.completions.create(
           
            model="openai/gpt-4.1-nano",
            messages=messages,
            tools=available_functions,
            tool_choice="auto"
        )
        # print("completion -----\n",completion)
        assistant_message = completion.choices[0].message
        
        # Check if the model wants to call a tool
        if assistant_message.tool_calls:
            # Handle tool calls
            tool_responses = handle_tool_calls(assistant_message.tool_calls)
            
            # Add assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function", 
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in assistant_message.tool_calls
                ]
            })
            
            # Add tool responses to conversation
            for tool_response in tool_responses:
                messages.append(tool_response)
            
            # Get final response from OpenAI
            final_completion = client.chat.completions.create(
                # extra_headers={
                #     "HTTP-Referer": "https://example.com",
                #     "X-Title": "MCP Tool Example",
                # },
                model="openai/gpt-4.1-nano",
                messages=messages,
                tools=available_functions,
                tool_choice="none"  # Don't use tools for this response
            )
            
            final_message = final_completion.choices[0].message
            messages.append({"role": "assistant", "content": final_message.content})
            
            print(f"\nAssistant: {final_message.content}")
        else:
            # No tool calls, just regular response
            messages.append({"role": "assistant", "content": assistant_message.content})
            print(f"\nAssistant: {assistant_message.content}")

# Run the chat interaction
if __name__ == "__main__":
    try:
        chat_with_exam_bot()
    finally:
        # Clean up the subprocess when done
        server.terminate()
        print("\nServer terminated.")