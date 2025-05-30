# llm.py (updated version)
import json
import subprocess
import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from database.monogodb import MongoDB

# Initialize MongoDB
mongo_db = MongoDB()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    base_url= "http://127.0.0.1:8080/v1",
    api_key= "gaia",
)

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
    server_output = json.loads(server.stdout.readline())
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
        
        id = tool_call.id  
        tool_call_message = create_message("tools/call", {
            "name": function_name,
            "arguments": function_args,
        }, id)
        
        send_message(tool_call_message)
        tool_result = receive_message()
        
        result_text = " "
        # Extract the result text
        if tool_result.get("content"):
            for content in tool_result["content"]:
                result_text += content["text"]
        else:
            result_text += ("No result")
            
        tool_responses.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": result_text
        })
        
    return tool_responses

def format_context_for_llm(context):
    """Convert context list to formatted string for LLM"""
    if not context or (len(context) == 1 and not context[0]["user_query"]):
        return "No previous conversation history."
    
    formatted_context = "Previous conversation history:\n"
    for entry in context:
        if entry["user_query"]:
            formatted_context += f"User: {entry['user_query']}\n"
        if entry["agent_response"]:
            formatted_context += f"Assistant: {entry['agent_response']}\n"
        if entry["tool_response"]:
            formatted_context += f"Tool Result: {entry['tool_response']}\n"
        formatted_context += "\n"
    
    return formatted_context

def chat_with_exam_bot():
    # This function is now only for CLI usage if needed
    user_id = input("Enter your user ID: ")

    user_context = mongo_db.get_user_context(user_id)
    context_string = format_context_for_llm(user_context)
    
    messages = [
        {"role": "system", "content": f"""You are a helpful AI assistant specialized in answering questions and providing practice questions. You have access to two tools:

1. get_random_question: Fetches random questions based on difficulty and topic
2. get_question_and_answer: Searches for relevant question-answer pairs from the dataset

Guidelines:
- When a user asks for practice questions, random questions, or wants to test their knowledge, ask them to specify:
  * Difficulty level (beginner, intermediate, advanced) - if they don't specify or say "any", use None
  * Topic - if they say "any topic" or don't specify, use None
- Always search the dataset first when users ask specific questions
- If you find the answer in the dataset, provide it directly
- Be conversational and helpful

Context from previous conversations:
{context_string}"""}
    ]
    
    while True:
        user_input = input("\nYour question (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        
        messages.append({"role": "user", "content": user_input})
        
        completion = client.chat.completions.create(
            model="llama3",
            messages=messages,
            tools=available_functions,
            tool_choice="auto"
        )
        
        assistant_message = completion.choices[0].message
        tool_response_content = ""
        
        if assistant_message.tool_calls:
            tool_responses = handle_tool_calls(assistant_message.tool_calls)
            tool_response_content = json.dumps([resp["content"] for resp in tool_responses])
            
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
            
            for tool_response in tool_responses:
                messages.append(tool_response)
            
            final_completion = client.chat.completions.create(
                model="llama3",
                messages=messages,
                tools=available_functions,
                tool_choice="none"
            )
            
            final_message = final_completion.choices[0].message
            messages.append({"role": "assistant", "content": final_message.content})
            
            print(f"\nAssistant: {final_message.content}")
            
            new_context_entry = {
                "user_query": user_input,
                "agent_response": final_message.content,
                "tool_response": tool_response_content
            }
            
        else:
            messages.append({"role": "assistant", "content": assistant_message.content})
            print(f"\nAssistant: {assistant_message.content}")
            
            new_context_entry = {
                "user_query": user_input,
                "agent_response": assistant_message.content,
                "tool_response": ""
            }
        
        # No longer limiting to 10 messages - removed the length check
        if user_context and len(user_context) == 1 and not user_context[0]["user_query"]:
            user_context[0] = new_context_entry
        else:
            user_context.append(new_context_entry)
        
        mongo_db.update_user_context(user_id, user_context)

if __name__ == "__main__":
    try:
        chat_with_exam_bot()
    finally:
        server.terminate()
        print("\nServer terminated.")