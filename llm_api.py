# llm_api.py (new file for API integration)
import json
import subprocess
import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from database.monogodb import MongoDB


mongo_db = MongoDB()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    base_url= "http://127.0.0.1:8080/v1",
    api_key= "gaia",
)

# Global server instance
server = None

def initialize_mcp_server():
    """Initialize the MCP server"""
    global server
    server = subprocess.Popen(
        ['python3', 'main.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
    )
    

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
    
    send_message(init_message)
    response = receive_message()
    
    init_complete_message = create_message("notifications/initialized", {})
    send_message(init_complete_message)
    
    # Get the list of available tools
    id += 1
    list_tools_message = create_message("tools/list", {}, id)
    send_message(list_tools_message)
    tools_response = receive_message()
    
    available_functions = []
    for tool in tools_response["tools"]:
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
    
    return available_functions

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
    global server
    server.stdin.write(message + "\n")
    server.stdin.flush()

def receive_message():
    global server
    server_output = json.loads(server.stdout.readline())
    if "result" in server_output:
        return server_output["result"]
    else:
        return "Error"

def handle_tool_calls(tool_calls):
    """Handle tool calls and get responses"""
    tool_responses = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        id = tool_call.id  
        tool_call_message = create_message("tools/call", {
            "name": function_name,
            "arguments": function_args,
        }, id)
        
        send_message(tool_call_message)
        tool_result = receive_message()
        
        result_text = " "
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

async def process_message(session_id, user_input, available_functions):
    """Process a user message and return the response"""
    # Get session context
    session_context = mongo_db.get_session_context(session_id)
    context_string = format_context_for_llm(session_context)
    
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
    

    for entry in session_context:
        if entry.get("user_query"):
            messages.append({"role": "user", "content": entry["user_query"]})
        if entry.get("agent_response"):
            messages.append({"role": "assistant", "content": entry["agent_response"]})
    

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
        response_text = final_message.content
    else:
        response_text = assistant_message.content
    

    new_context_entry = {
        "user_query": user_input,
        "agent_response": response_text,
        "tool_response": tool_response_content
    }
    
    session_context.append(new_context_entry)
    mongo_db.update_session_context(session_id, session_context)
    
    return response_text

def cleanup_server():
    """Cleanup the MCP server"""
    global server
    if server:
        server.terminate()